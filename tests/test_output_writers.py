"""Unit tests for the stdout/stderr fan-out writers.

`QueueWriter` turns line-buffered writes into individual queue messages (used to
stream console output to the dashboard); `MultiWriter` tees writes to several
file-like objects at once. Both are pure and are sent across processes, so
pickling is part of the contract.
"""

import pickle
from unittest.mock import MagicMock

from src.utils.outputWriters import QueueWriter, MultiWriter


class FakeQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


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
