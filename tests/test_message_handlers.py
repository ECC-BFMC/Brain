"""Unit tests for the message sender and subscriber.

These are the plumbing every process uses to talk over the multiprocessing
queues/pipes. The sender formats and enqueues messages; the subscriber pulls
them off an internal pipe with FIFO or last-only semantics. Both are tested
without real processes:
  * the sender is given a dict of fake queues that just record `.put(...)`;
  * the subscriber is fed by writing into the send end of its own pipe, exactly
    as the gateway does at runtime ({"Type", "value", "id", "Owner"}).
"""

import pytest

from src.utils.messages.messageHandlerSender import messageHandlerSender
from src.utils.messages.messageHandlerSubscriber import messageHandlerSubscriber
from src.utils.messages.allMessages import StateChange


class FakeQueue:
    """Minimal stand-in for a multiprocessing.Queue that records puts."""

    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


@pytest.fixture
def queues():
    # Cover every queue name a message might target, plus Config for (un)subscribe.
    return {name: FakeQueue() for name in ("Critical", "Warning", "General", "Config", "Log")}


def gateway_envelope(message_enum, value):
    """Build the pipe payload shape the gateway sends to subscribers."""
    return {
        "Type": message_enum.msgType.value,
        "value": value,
        "id": message_enum.msgID.value,
        "Owner": message_enum.Owner.value,
    }


# --------------------------------------------------------------------------- #
# Sender
# --------------------------------------------------------------------------- #
def test_sender_puts_on_the_messages_queue(queues):
    sender = messageHandlerSender(queues, StateChange)
    sender.send("AUTO")

    target = queues[StateChange.Queue.value]  # StateChange -> "Critical"
    assert len(target.items) == 1
    assert target.items[0] == {
        "Owner": StateChange.Owner.value,
        "msgID": StateChange.msgID.value,
        "msgType": StateChange.msgType.value,
        "msgValue": "AUTO",
    }


def test_sender_does_not_touch_other_queues(queues):
    messageHandlerSender(queues, StateChange).send("STOP")
    for name, q in queues.items():
        if name != StateChange.Queue.value:
            assert q.items == []


def test_sender_preserves_value_object_identity(queues):
    """The value is passed through untouched (not stringified/copied)."""
    payload = {"nested": [1, 2, 3]}
    sender = messageHandlerSender(queues, StateChange)
    sender.send(payload)
    assert sender.queuesList[StateChange.Queue.value].items[0]["msgValue"] is payload


# --------------------------------------------------------------------------- #
# Subscriber
# --------------------------------------------------------------------------- #
def test_receive_returns_none_when_pipe_empty(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    assert sub.receive() is None


def test_fifo_returns_messages_in_order(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    for value in ("AUTO", "MANUAL", "STOP"):
        sub._pipeSend.send(gateway_envelope(StateChange, value))

    assert sub.receive() == "AUTO"
    assert sub.receive() == "MANUAL"
    assert sub.receive() == "STOP"
    assert sub.receive() is None


def test_lastonly_drains_to_most_recent(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "lastonly")
    for value in ("AUTO", "MANUAL", "STOP"):
        sub._pipeSend.send(gateway_envelope(StateChange, value))

    # A single receive collapses the backlog to the newest value...
    assert sub.receive() == "STOP"
    # ...and the pipe is now empty.
    assert sub.receive() is None


def test_bad_delivery_mode_falls_back_to_fifo(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "not-a-mode")
    assert sub._deliveryMode == "fifo"


def test_delivery_mode_is_case_insensitive(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "LastOnly")
    assert sub._deliveryMode == "lastonly"


def test_empty_drains_the_pipe(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    for value in ("AUTO", "MANUAL"):
        sub._pipeSend.send(gateway_envelope(StateChange, value))

    assert sub.is_data_in_pipe() is True
    sub.empty()
    assert sub.is_data_in_pipe() is False
    assert sub.receive() is None


def test_subscribe_puts_request_on_config_queue(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    sub.subscribe()

    assert len(queues["Config"].items) == 1
    req = queues["Config"].items[0]
    assert req["Subscribe/Unsubscribe"] == "subscribe"
    assert req["Owner"] == StateChange.Owner.value
    assert req["msgID"] == StateChange.msgID.value
    assert "pipe" in req["To"]


def test_unsubscribe_puts_request_on_config_queue(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    sub.unsubscribe()

    req = queues["Config"].items[-1]
    assert req["Subscribe/Unsubscribe"] == "unsubscribe"
    assert req["Owner"] == StateChange.Owner.value
    assert req["msgID"] == StateChange.msgID.value


def test_auto_subscribe_flag_registers_on_construction(queues):
    messageHandlerSubscriber(queues, StateChange, "fifo", subscribe=True)
    assert len(queues["Config"].items) == 1
    assert queues["Config"].items[0]["Subscribe/Unsubscribe"] == "subscribe"


def test_delivery_mode_toggles(queues):
    sub = messageHandlerSubscriber(queues, StateChange, "fifo")
    sub.set_delivery_mode_to_last_only()
    assert sub._deliveryMode == "lastonly"
    sub.set_delivery_mode_to_fifo()
    assert sub._deliveryMode == "fifo"
