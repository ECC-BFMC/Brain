"""Unit tests for the ThreadWithStop base class.

Every worker thread in the project extends ThreadWithStop for its pause/resume/
stop lifecycle. The state transitions are pure; a short real-thread run confirms
that stop() actually terminates a running loop (including when paused).
"""

import threading
import time

import pytest

from src.templates.threadwithstop import ThreadWithStop


def test_starts_in_running_state():
    t = ThreadWithStop()
    assert t.is_paused() is False


def test_pause_and_resume_toggle_state():
    t = ThreadWithStop()
    t.pause()
    assert t.is_paused() is True
    t.resume()
    assert t.is_paused() is False


def test_bound_method_target_is_rejected():
    obj = ThreadWithStop()
    with pytest.raises(ValueError):
        ThreadWithStop(target=obj.run)  # bound method -> not allowed


def test_unbound_target_is_wrapped_and_accepted():
    def worker(self):
        pass

    # Should not raise; the instance is bound in as the first arg.
    ThreadWithStop(target=worker)


def test_stop_resumes_a_paused_thread():
    t = ThreadWithStop()
    t.pause()
    t.stop()
    # stop() resumes first so the loop can observe the stop signal.
    assert t.is_paused() is False
    assert t._blocker.is_set() is True


def test_running_thread_stops_and_joins():
    counter = {"n": 0}

    class Counter(ThreadWithStop):
        def thread_work(self):
            counter["n"] += 1

    t = Counter(pause=0.001)
    t.start()
    time.sleep(0.05)
    t.stop()
    t.join(timeout=2)
    assert not t.is_alive()
    assert counter["n"] > 0  # the loop actually ran


def test_paused_thread_does_no_work_then_resumes():
    counter = {"n": 0}

    class Counter(ThreadWithStop):
        def thread_work(self):
            counter["n"] += 1

    t = Counter(pause=0.001)
    t.pause()
    t.start()
    time.sleep(0.03)
    paused_count = counter["n"]
    assert paused_count == 0  # nothing ran while paused

    t.resume()
    time.sleep(0.03)
    t.stop()
    t.join(timeout=2)
    assert counter["n"] > paused_count
