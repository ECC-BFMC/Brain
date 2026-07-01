import os
import re
import sys
import glob
import time
import logging

# Directory where run log files are stored.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(_REPO_ROOT, "runtime", "temp")

# How many past runs to keep before the oldest gets overwritten.
MAX_RUNS = 3

# Env var used to share a single run timestamp across all (spawned) processes,
# so every process of the same run writes into the same pair of files.
_RUN_TS_ENV = "BRAIN_RUN_TS"

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_CONSOLE_TIME_FORMAT = "%H:%M:%S"

# Strips ANSI colour escape codes so the files stay plain text.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Console colours, matching the project's existing print() style.
_RESET = "\033[0m"
_LABEL_COLOR = "\033[1;97m"      # bright white component label
_LEVEL_COLORS = {
    "DEBUG": "\033[1;96m",       # cyan
    "INFO": "\033[1;92m",        # green
    "WARNING": "\033[1;93m",     # yellow
    "ERROR": "\033[1;91m",       # red
    "CRITICAL": "\033[1;91m",    # red
}


def timestamp():
    """Current time formatted like the log files' line timestamps."""
    return time.strftime(_DATE_FORMAT)


def get_logger(name):
    """Return a component logger, e.g. get_logger('Serial Handler').

    The name becomes the ``[ Serial Handler ]`` label in the output.
    """
    return logging.getLogger(name)


class _ComponentFormatter(logging.Formatter):
    """Renders records as ``<time> [ Component ] : LEVEL - message``.

    With ``color=True`` (console) the label, level and body are coloured like
    the project's original prints; with ``color=False`` (files) it's plain text.
    """

    def __init__(self, color, datefmt):
        super().__init__(datefmt=datefmt)
        self._color = color

    def format(self, record):
        ts = self.formatTime(record, self.datefmt)
        name = record.name
        level = record.levelname
        msg = record.getMessage()
        if record.exc_info:
            msg = msg + "\n" + self.formatException(record.exc_info)

        if self._color:
            lvl = f"{_LEVEL_COLORS.get(level, '')}{level}{_RESET}"
            return f"{ts} {_LABEL_COLOR}[ {name} ] :{_RESET} {lvl} - {msg}"
        return f"{ts} [ {name} ] : {level} - {msg}"


class _StreamTee:
    """File-like object: writes to the original stream and appends clean,
    timestamped lines to one or more log files."""

    def __init__(self, original, file_paths):
        self._original = original
        self._file_paths = file_paths
        self._buffer = ""

    def write(self, msg):
        self._original.write(msg)
        self._buffer += msg
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            clean = _ANSI_RE.sub("", line)
            if not clean.strip():
                continue
            stamped = time.strftime(_DATE_FORMAT + " ") + clean + "\n"
            for path in self._file_paths:
                try:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write(stamped)
                except OSError:
                    pass

    def flush(self):
        self._original.flush()

    def isatty(self):
        return getattr(self._original, "isatty", lambda: False)()


def _prune_old_runs():
    """Keep only the most recent (MAX_RUNS - 1) runs so the new run makes MAX_RUNS."""
    timestamps = set()
    for path in glob.glob(os.path.join(LOG_DIR, "info_*.log")) + \
            glob.glob(os.path.join(LOG_DIR, "error_*.log")):
        base = os.path.basename(path)
        ts = base.split("_", 1)[1].rsplit(".log", 1)[0]
        timestamps.add(ts)

    for ts in sorted(timestamps)[:-(MAX_RUNS - 1) or None]:
        for prefix in ("info", "error"):
            f = os.path.join(LOG_DIR, f"{prefix}_{ts}.log")
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass


def setup_logging(level=logging.INFO):
    """Configure root logger + stdout/stderr capture into per-run files.

    Call once per process at import time. The parent process picks the run
    timestamp and prunes old runs; spawned children inherit the timestamp via an
    environment variable and write into the same files. Both ``logging`` records
    and plain ``print()`` output are captured, so the existing print-based
    process logs end up in the files too.
    """
    run_ts = os.environ.get(_RUN_TS_ENV)
    is_parent = run_ts is None
    if is_parent:
        run_ts = time.strftime("%Y%m%d_%H%M%S")
        os.environ[_RUN_TS_ENV] = run_ts

    os.makedirs(LOG_DIR, exist_ok=True)
    if is_parent:
        _prune_old_runs()

    info_path = os.path.join(LOG_DIR, f"info_{run_ts}.log")
    error_path = os.path.join(LOG_DIR, f"error_{run_ts}.log")

    console_formatter = _ComponentFormatter(color=True, datefmt=_CONSOLE_TIME_FORMAT)
    file_formatter = _ComponentFormatter(color=False, datefmt=_DATE_FORMAT)

    # Console handler binds to the *original* stderr (created before the tees
    # below), so logging records aren't double-written into the files.
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(console_formatter)

    info_file = logging.FileHandler(info_path, encoding="utf-8")
    info_file.setLevel(logging.INFO)
    info_file.setFormatter(file_formatter)

    error_file = logging.FileHandler(error_path, encoding="utf-8")
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(file_formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(info_file)
    root.addHandler(error_file)

    # Capture plain print() output: stdout -> info file, stderr -> both files.
    if not isinstance(sys.stdout, _StreamTee):
        sys.stdout = _StreamTee(sys.stdout, [info_path])
    if not isinstance(sys.stderr, _StreamTee):
        sys.stderr = _StreamTee(sys.stderr, [info_path, error_path])
