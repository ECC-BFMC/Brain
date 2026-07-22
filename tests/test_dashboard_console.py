"""Regression tests for the dashboard's terminal-output stream."""

import ast
import queue
from collections import deque
from pathlib import Path
from threading import Lock
from types import SimpleNamespace


def load_console_methods():
    dashboard_path = Path(__file__).parents[1] / "src" / "dashboard" / "processDashboard.py"
    tree = ast.parse(dashboard_path.read_text(encoding="utf-8"))
    process_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "processDashboard"
    )
    wanted = {"stream_console_logs", "handle_console_connect"}
    methods = [
        node for node in process_class.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace = {
        "queue": queue,
        "request": SimpleNamespace(sid=None),
    }
    exec(compile(ast.Module(body=methods, type_ignores=[]), dashboard_path, "exec"), namespace)
    return namespace


CONSOLE_METHODS = load_console_methods()


class FakeSocket:
    def __init__(self, owner=None):
        self.owner = owner
        self.emitted = []

    def emit(self, event, payload, room=None):
        self.emitted.append((event, payload, room))
        if self.owner is not None:
            self.owner.running = False

    def sleep(self, _delay):
        pass


class OneMessageQueue:
    def get(self, timeout):
        assert timeout == 0.1
        return "terminal line"


def test_stream_uses_blocking_get_and_records_terminal_history():
    dashboard = SimpleNamespace(
        queueList={"Log": OneMessageQueue()},
        running=True,
        socketio=None,
        console_history=deque(maxlen=500),
        console_history_lock=Lock(),
        debugging=False,
    )
    dashboard.socketio = FakeSocket(dashboard)

    CONSOLE_METHODS["stream_console_logs"](dashboard)

    assert list(dashboard.console_history) == ["terminal line"]
    assert dashboard.socketio.emitted == [
        ("console_log", {"data": "terminal line"}, None),
    ]


def test_connect_replays_terminal_history_only_to_new_client():
    socket = FakeSocket()
    dashboard = SimpleNamespace(
        socketio=socket,
        console_history=deque(["first", "second"], maxlen=500),
        console_history_lock=Lock(),
    )
    CONSOLE_METHODS["request"] = SimpleNamespace(sid="client-1")

    CONSOLE_METHODS["handle_console_connect"](dashboard)

    assert socket.emitted == [
        ("console_log", {"data": "first"}, "client-1"),
        ("console_log", {"data": "second"}, "client-1"),
    ]


def test_thread_only_console_state_is_created_after_process_spawn():
    dashboard_path = Path(__file__).parents[1] / "src" / "dashboard" / "processDashboard.py"
    tree = ast.parse(dashboard_path.read_text(encoding="utf-8"))
    process_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "processDashboard"
    )
    methods = {
        node.name: node for node in process_class.body
        if isinstance(node, ast.FunctionDef) and node.name in {"__init__", "run"}
    }

    def assigned_attributes(method):
        return {
            target.attr
            for node in ast.walk(method)
            for target in getattr(node, "targets", [])
            if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        }

    assert "console_history_lock" not in assigned_attributes(methods["__init__"])
    assert "console_history_lock" in assigned_attributes(methods["run"])
