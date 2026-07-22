"""Unit tests for the stdout/stderr fan-out writers.

`QueueWriter` turns line-buffered writes into individual queue messages (used to
stream console output to the dashboard); `MultiWriter` tees writes to several
file-like objects at once. Both are pure and are sent across processes, so
pickling is part of the contract.
"""

import pickle
import multiprocessing
import logging
from io import StringIO
from unittest.mock import MagicMock

from src.utils.outputWriters import QueueWriter, MultiWriter
from src.utils import logConfig


class FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


def emit_dashboard_output_from_spawned_child(log_queue):
    """Exercise the fresh logging state used by spawn/forkserver children."""
    terminal = StringIO()
    root = logging.getLogger()
    console = logging.StreamHandler(terminal)
    console._brain_console_handler = True
    console.addFilter(logConfig._NoFileOnlyFilter())
    root.handlers = [console]
    root.setLevel(logging.INFO)

    logConfig.sys.stdout = terminal
    logConfig.sys.stderr = terminal
    logConfig.configure_dashboard_output(log_queue)
    logConfig.sys.stdout.write("child print\n")
    logConfig.get_logger("Child").info("child logger")
    logConfig.get_logger("Child").info("file only", extra={"file_only": True})


def test_complete_line_is_enqueued():
    q = FakeQueue()
    QueueWriter(q).write("hello\n")
    assert q.items == ["hello"]


def test_partial_line_is_buffered_until_newline():
    q = FakeQueue()
    w = QueueWriter(q)
    w.write("no newline yet")
    assert q.items == []
    w.write(" and the rest\n")
    assert q.items == ["no newline yet and the rest"]


def test_multiple_lines_in_one_write_split_into_messages():
    q = FakeQueue()
    QueueWriter(q).write("a\nb\nc\n")
    assert q.items == ["a", "b", "c"]


def test_blank_and_whitespace_lines_are_dropped():
    q = FakeQueue()
    w = QueueWriter(q)
    w.write("\n")
    w.write("   \n")
    w.write("real\n")
    assert q.items == ["real"]


def test_queuewriter_is_picklable_after_use():
    """The writer is handed to child processes; pickling must survive even after
    the thread-local buffer has been created."""
    q = FakeQueue()
    w = QueueWriter(q)
    w.write("prime the buffer")  # creates _local
    restored = pickle.loads(pickle.dumps(w))
    # The restored writer still enqueues on its (restored) queue.
    restored.write("after unpickle\n")
    assert restored.queue.items == ["after unpickle"]


def test_multiwriter_fans_out_write_and_flush():
    a, b = MagicMock(), MagicMock()
    mw = MultiWriter(a, b)
    mw.write("msg")
    mw.flush()
    a.write.assert_called_once_with("msg")
    b.write.assert_called_once_with("msg")
    a.flush.assert_called_once()
    b.flush.assert_called_once()


def test_multiwriter_with_no_writers_is_noop():
    mw = MultiWriter()
    mw.write("nothing")  # must not raise
    mw.flush()


def test_dashboard_sink_receives_only_console_visible_logging():
    terminal = StringIO()
    queue = FakeQueue()
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level

    console = logging.StreamHandler(terminal)
    console._brain_console_handler = True
    console.addFilter(logConfig._NoFileOnlyFilter())

    try:
        root.handlers = [console]
        root.setLevel(logging.INFO)
        logConfig.add_console_sink(QueueWriter(queue))

        logger = logConfig.get_logger("Test")
        logger.info("visible in terminal and dashboard")
        logger.info("runtime file only", extra={"file_only": True})

        terminal_line = terminal.getvalue().strip()
        assert queue.items == [terminal_line]
        assert "visible in terminal and dashboard" in terminal_line
        assert "runtime file only" not in terminal.getvalue()
    finally:
        console.close()
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_dashboard_output_configuration_is_idempotent(monkeypatch):
    terminal = StringIO()
    queue = FakeQueue()
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    console = logging.StreamHandler(terminal)
    console._brain_console_handler = True

    try:
        root.handlers = [console]
        root.setLevel(logging.INFO)
        monkeypatch.setattr(logConfig.sys, "stdout", terminal)
        monkeypatch.setattr(logConfig.sys, "stderr", terminal)

        logConfig.configure_dashboard_output(queue)
        logConfig.configure_dashboard_output(queue)
        logConfig.sys.stdout.write("one line\n")
        logConfig.get_logger("Test").info("one log")

        assert queue.items == ["one line", "one log"]
    finally:
        console.close()
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_spawned_child_forwards_prints_and_console_logs_only():
    context = multiprocessing.get_context("spawn")
    log_queue = context.Queue()
    child = context.Process(
        target=emit_dashboard_output_from_spawned_child,
        args=(log_queue,),
    )

    child.start()
    child.join(timeout=10)

    assert child.exitcode == 0
    assert [log_queue.get(timeout=2), log_queue.get(timeout=2)] == [
        "child print",
        "child logger",
    ]
