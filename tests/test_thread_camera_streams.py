"""Tests for demand-driven camera stream publishing.

The camera publishes a stream (raw frame into shared memory + a notification
dict through the gateway queues) only while the stream's sender reports
hasSubscribers(), fed by the gateway through the sender's feedback pipe.
Exercised in mock mode so no picamera2 is needed; demand is injected through
the senders' real feedback pipes.
"""

import queue as queue_module
from multiprocessing import Queue

import pytest

import src.hardware.camera.threads.threadCamera as thread_camera_module
from src.hardware.camera.threads.threadCamera import threadCamera
from src.utils.sharedFrameBuffer import SharedFrameReader


@pytest.fixture
def camera(monkeypatch):
    # the dev-mode branch sleeps 1s per frame; skip that in tests
    monkeypatch.setattr(thread_camera_module.time, "sleep", lambda seconds: None)
    queues = {name: Queue() for name in ("Critical", "Warning", "General", "Config")}
    cam = threadCamera(queues, False, use_mock=True)
    yield cam, queues
    cam.stop()


def set_demand(sender, count):
    """Feed a subscriber count into the sender exactly as the gateway would."""
    sender._pipeSend.send(count)


def get_notification(queues, msg_id, timeout=2):
    """Returns the first threadCamera envelope with the given msgID, skipping
    unrelated messages (e.g. the Recording flag from housekeeping)."""
    while True:
        envelope = queues["General"].get(timeout=timeout)
        if envelope["Owner"] == "threadCamera" and envelope["msgID"] == msg_id:
            return envelope


def test_no_demand_publishes_no_stream(camera):
    cam, _ = camera
    cam.thread_work()
    assert cam._streams["serialCamera"]["writer"] is None
    assert cam._streams["mainCamera"]["writer"] is None


def test_demanded_serial_stream_is_published(camera):
    cam, queues = camera
    set_demand(cam.serialCameraSender, 1)
    cam.thread_work()

    envelope = get_notification(queues, msg_id=2)
    notification = envelope["msgValue"]
    assert notification["seq"] == 1

    reader = SharedFrameReader(name=notification["shm"], shape=tuple(notification["shape"]))
    try:
        frame, timestamp, seq = reader.readLatest()
        assert seq == 1
        assert frame.shape == (270, 512, 3)
        assert timestamp == notification["timestamp"]
    finally:
        reader.close()

    # the undemanded main stream must not have been produced
    assert cam._streams["mainCamera"]["writer"] is None


def test_demanded_main_stream_is_published(camera):
    cam, queues = camera
    set_demand(cam.mainCameraSender, 1)
    cam.thread_work()

    envelope = get_notification(queues, msg_id=1)
    assert tuple(envelope["msgValue"]["shape"]) == (1080, 2048, 3)
    assert cam._streams["serialCamera"]["writer"] is None


def test_demand_stops_publishing_when_it_drops_to_zero(camera):
    cam, queues = camera
    set_demand(cam.serialCameraSender, 1)
    cam.thread_work()
    get_notification(queues, msg_id=2)

    set_demand(cam.serialCameraSender, 0)
    cam.thread_work()
    with pytest.raises(queue_module.Empty):
        get_notification(queues, msg_id=2, timeout=0.3)
