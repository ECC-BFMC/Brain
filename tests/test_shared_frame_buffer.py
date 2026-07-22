"""Unit tests for the shared-memory camera frame ring buffer.

The writer (camera process) publishes raw frames; readers (perception
processes) attach by name and always get the newest fully-written frame.
Exercised here in-process: shared_memory segments are addressable by name
within the same process exactly as across processes.
"""

import sys

import numpy as np
import pytest

from src.utils.sharedFrameBuffer import NotifiedFrameReader, SharedFrameReader, SharedFrameWriter

SHM_NAME = "bfmc_test_frames"
SHAPE = (4, 6, 3)


def make_frame(fill):
    return np.full(SHAPE, fill, dtype=np.uint8)


@pytest.fixture
def buffer_pair():
    writer = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=1)
    reader = SharedFrameReader(name=SHM_NAME, shape=SHAPE, history=1)
    yield writer, reader
    reader.close()
    writer.close()


def test_read_before_first_write_returns_none(buffer_pair):
    _, reader = buffer_pair
    assert reader.readLatest() is None


def test_roundtrip_frame_timestamp_and_seq(buffer_pair):
    writer, reader = buffer_pair
    frame = make_frame(42)
    writer.write(frame, timestamp=123.5)

    got_frame, timestamp, seq = reader.readLatest()
    assert np.array_equal(got_frame, frame)
    assert timestamp == 123.5
    assert seq == 1


def test_latest_frame_wins(buffer_pair):
    writer, reader = buffer_pair
    for i in range(1, 6):
        writer.write(make_frame(i))

    got_frame, _, seq = reader.readLatest()
    assert seq == 5
    assert np.array_equal(got_frame, make_frame(5))


def test_returned_frame_is_a_copy(buffer_pair):
    writer, reader = buffer_pair
    writer.write(make_frame(1))
    got_frame, _, _ = reader.readLatest()
    writer.write(make_frame(2))
    # the copy taken at read time must not change when the writer overwrites slots
    assert np.array_equal(got_frame, make_frame(1))


def test_wrong_shape_or_dtype_is_rejected(buffer_pair):
    writer, _ = buffer_pair
    with pytest.raises(ValueError):
        writer.write(np.zeros((2, 2, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        writer.write(np.zeros(SHAPE, dtype=np.float32))


def test_reader_rejects_mismatched_geometry():
    writer = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=1)
    try:
        with pytest.raises(ValueError):
            SharedFrameReader(name=SHM_NAME, shape=(1080, 2048, 3), history=1)
    finally:
        writer.close()


def test_reader_auto_discovers_writer_history():
    writer = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=4)
    reader = SharedFrameReader(name=SHM_NAME, shape=SHAPE)
    try:
        assert reader.history == 4
        for i in range(1, 6):
            writer.write(make_frame(i), timestamp=float(i))

        got_frame, timestamp, seq = reader.readBack(4)
        assert seq == 1
        assert timestamp == 1.0
        assert np.array_equal(got_frame, make_frame(1))
    finally:
        reader.close()
        writer.close()


def test_read_back_uses_public_history_window():
    writer = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=2)
    reader = SharedFrameReader(name=SHM_NAME, shape=SHAPE)
    try:
        for i in range(1, 5):
            writer.write(make_frame(i))

        latest_frame, _, latest_seq = reader.readBack(0)
        assert latest_seq == 4
        assert np.array_equal(latest_frame, make_frame(4))

        previous_frame, _, previous_seq = reader.readBack(1)
        assert previous_seq == 3
        assert np.array_equal(previous_frame, make_frame(3))

        oldest_frame, _, oldest_seq = reader.readBack(2)
        assert oldest_seq == 2
        assert np.array_equal(oldest_frame, make_frame(2))

        assert reader.readBack(3) is None
        assert reader.readSeq(1) is None
    finally:
        reader.close()
        writer.close()


def test_read_seq_rejects_never_written_and_future_sequences(buffer_pair):
    writer, reader = buffer_pair
    assert reader.readSeq(1) is None

    writer.write(make_frame(1))
    assert reader.readSeq(2) is None


def test_invalid_buffer_size_is_rejected():
    with pytest.raises(ValueError):
        SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=-1)


def notification(seq=1, shm=SHM_NAME):
    return {"seq": seq, "timestamp": 0.0, "shm": shm, "shape": list(SHAPE)}


def test_notified_reader_returns_each_frame_once(buffer_pair):
    writer, _ = buffer_pair
    frameReader = NotifiedFrameReader()
    try:
        writer.write(make_frame(1))
        frame, _, seq = frameReader.read(notification(seq=1))
        assert seq == 1
        assert np.array_equal(frame, make_frame(1))

        # same newest frame again -> already delivered
        assert frameReader.read(notification(seq=1)) is None

        writer.write(make_frame(2))
        _, _, seq = frameReader.read(notification(seq=2))
        assert seq == 2
    finally:
        frameReader.close()


def test_notified_reader_returns_none_while_segment_missing():
    frameReader = NotifiedFrameReader()
    try:
        assert frameReader.read(notification(shm="bfmc_test_nonexistent")) is None
    finally:
        frameReader.close()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows frees segments when the last handle closes; stale segments only exist on POSIX",
)
def test_writer_replaces_stale_segment():
    # a "crashed" writer that never unlinked must not block the next run
    stale = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=1)
    writer = SharedFrameWriter(name=SHM_NAME, shape=SHAPE, history=1)
    reader = SharedFrameReader(name=SHM_NAME, shape=SHAPE, history=1)
    try:
        writer.write(make_frame(7))
        got_frame, _, _ = reader.readLatest()
        assert np.array_equal(got_frame, make_frame(7))
    finally:
        reader.close()
        writer.close()
        stale.close()
