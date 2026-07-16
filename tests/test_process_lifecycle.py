import ast
from pathlib import Path


class FakeLogger:
    def warning(self, message):
        pass

    def info(self, message):
        pass


def load_lifecycle_functions():
    main_path = Path(__file__).parents[1] / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    wanted = {"shutdown_process", "manage_process_life"}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"get_logger": lambda name: FakeLogger()}
    exec(compile(ast.Module(body=functions, type_ignores=[]), main_path, "exec"), namespace)
    return namespace["manage_process_life"]


manage_process_life = load_lifecycle_functions()

class FakeProcess:
    def __init__(self):
        self.alive = True
        self.stopped = False
        self.joined = False
        self.terminated = False
        self.killed = False

    def is_alive(self):
        return self.alive

    def stop(self):
        self.stopped = True
        self.alive = False

    def join(self, timeout):
        self.joined = True

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_disabling_dynamic_process_stops_it_before_joining():
    process = FakeProcess()
    processes = [process]

    result = manage_process_life(
        process_class=None,
        process_instance=process,
        process_args=(),
        enabled=False,
        allProcesses=processes,
    )

    assert result is None
    assert process.stopped
    assert process.joined
    assert not process.terminated
    assert not process.killed
    assert process not in processes