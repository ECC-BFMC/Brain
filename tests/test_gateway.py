"""Unit tests for the gateway message router (threadGateway).

The gateway is the process message bus: subscribers register a pipe for an
(Owner, msgID) pair, and send() fans a message out to every registered pipe.
This is the counterpart to the messageHandler tests and is exercised end-to-end
with real pipes.
"""

import logging
from multiprocessing import Pipe, Queue

import pytest

from src.gateway.threads.threadGateway import threadGateway


@pytest.fixture
def gateway():
    return threadGateway({}, False)


def sub_message(owner, msg_id, receiver, pipe):
    return {"Owner": owner, "msgID": msg_id, "To": {"receiver": receiver, "pipe": pipe}}


def send_message(owner, msg_id, value, msg_type="str"):
    return {"Owner": owner, "msgID": msg_id, "msgType": msg_type, "msgValue": value}


def test_subscribe_then_send_delivers_envelope(gateway):
    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("stateMachine", 1, "listener", send))
    gateway.send(send_message("stateMachine", 1, "AUTO"))

    assert recv.recv() == {"Type": "str", "value": "AUTO", "id": 1, "Owner": "stateMachine"}


def test_send_reaches_all_subscribers(gateway):
    recv_a, send_a = Pipe(duplex=False)
    recv_b, send_b = Pipe(duplex=False)
    gateway.subscribe(sub_message("owner", 2, "A", send_a))
    gateway.subscribe(sub_message("owner", 2, "B", send_b))

    gateway.send(send_message("owner", 2, "payload"))

    assert recv_a.recv()["value"] == "payload"
    assert recv_b.recv()["value"] == "payload"


def test_unsubscribe_stops_delivery(gateway):
    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("owner", 3, "A", send))
    gateway.unsubscribe({"Owner": "owner", "msgID": 3, "To": {"receiver": "A"}})

    assert gateway.messageApproved == []
    gateway.send(send_message("owner", 3, "dropped"))
    assert recv.poll() is False


def test_subscribe_and_unsubscribe_are_logged_file_only(gateway, caplog):
    recv, send = Pipe(duplex=False)
    with caplog.at_level(logging.INFO, logger="Gateway"):
        gateway.subscribe(sub_message("owner", 3, "A", send))
        gateway.unsubscribe({"Owner": "owner", "msgID": 3, "To": {"receiver": "A"}})

    records = [record for record in caplog.records if record.name == "Gateway"]
    assert [record.getMessage() for record in records] == [
        "Subscribed A to owner/3",
        "Unsubscribed A from owner/3",
    ]
    assert all(getattr(record, "file_only", False) for record in records)


def test_send_to_unapproved_pair_is_silently_dropped(gateway):
    # No subscription registered -> send must not raise (and nothing to receive).
    gateway.send(send_message("nobody", 99, "x"))
    assert ("nobody", 99) not in gateway.messageApproved


def test_duplicate_subscribe_keeps_single_pipe_but_approves_each(gateway):
    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("owner", 4, "same", send))
    gateway.subscribe(sub_message("owner", 4, "same", send))
    # Same receiver -> one pipe entry, but approval recorded twice.
    assert list(gateway.sendingList["owner"][4].keys()) == ["same"]
    assert gateway.messageApproved.count(("owner", 4)) == 2


def test_unsubscribe_unknown_subscription_does_not_raise(gateway):
    gateway.unsubscribe({"Owner": "ghost", "msgID": 9, "To": {"receiver": "X"}})
    assert gateway.messageApproved == []


def test_double_unsubscribe_does_not_raise(gateway):
    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("owner", 5, "A", send))
    unsub = {"Owner": "owner", "msgID": 5, "To": {"receiver": "A"}}
    gateway.unsubscribe(unsub)
    gateway.unsubscribe(unsub)
    assert gateway.messageApproved == []


def feedback_message(owner, msg_id, pipe):
    """Sender feedback registration as messageHandlerSender puts it on the Config queue."""
    return {"Subscribe/Unsubscribe": "senderFeedback", "Owner": owner, "msgID": msg_id, "To": {"pipe": pipe}}


def test_sender_registration_reports_current_count(gateway):
    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("threadCamera", 2, "dash", send))

    # a sender registered after the subscriber must start with the right count
    feedback_recv, feedback_send = Pipe(duplex=False)
    gateway.registerSender(feedback_message("threadCamera", 2, feedback_send))
    assert feedback_recv.recv() == 1


def test_sender_feedback_follows_subscribe_and_unsubscribe(gateway):
    feedback_recv, feedback_send = Pipe(duplex=False)
    gateway.registerSender(feedback_message("threadCamera", 2, feedback_send))
    assert feedback_recv.recv() == 0

    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("threadCamera", 2, "dash", send))
    assert feedback_recv.recv() == 1

    gateway.unsubscribe({"Owner": "threadCamera", "msgID": 2, "To": {"receiver": "dash"}})
    assert feedback_recv.recv() == 0


def test_sender_feedback_only_for_own_message(gateway):
    feedback_recv, feedback_send = Pipe(duplex=False)
    gateway.registerSender(feedback_message("threadCamera", 2, feedback_send))
    feedback_recv.recv()

    recv, send = Pipe(duplex=False)
    gateway.subscribe(sub_message("someoneElse", 7, "dash", send))
    assert feedback_recv.poll() is False


def make_queues():
    return {name: Queue() for name in ("Critical", "Warning", "General", "Config")}


def config_sub_message(owner, msg_id, receiver, pipe):
    """Subscribe request as it arrives on the Config queue (from messageHandlerSubscriber)."""
    return {"Subscribe/Unsubscribe": "subscribe", **sub_message(owner, msg_id, receiver, pipe)}


def pump(gateway, done, attempts=100):
    """Run thread_work until `done()` or the attempts run out (multiprocessing
    queues flush through a feeder thread, so the first calls may see nothing)."""
    for _ in range(attempts):
        gateway.thread_work()
        if done():
            return
    raise AssertionError("gateway did not process the expected messages in time")


def test_thread_work_applies_config_then_routes_data():
    queues = make_queues()
    gw = threadGateway(queues, False)
    recv, send = Pipe(duplex=False)

    queues["Config"].put(config_sub_message("owner", 7, "recv", send))
    pump(gw, lambda: ("owner", 7) in gw.messageApproved)

    queues["General"].put(send_message("owner", 7, "hello"))
    pump(gw, recv.poll)
    assert recv.recv()["value"] == "hello"


def test_thread_work_registers_sender_feedback():
    queues = make_queues()
    gw = threadGateway(queues, False)
    feedback_recv, feedback_send = Pipe(duplex=False)

    queues["Config"].put(feedback_message("threadCamera", 2, feedback_send))
    pump(gw, feedback_recv.poll)
    assert feedback_recv.recv() == 0


def test_thread_work_delivers_critical_before_general():
    queues = make_queues()
    gw = threadGateway(queues, False)
    recv, send = Pipe(duplex=False)

    queues["Config"].put(config_sub_message("owner", 1, "recv", send))
    queues["Config"].put(config_sub_message("owner", 2, "recv", send))
    pump(gw, lambda: gw.messageApproved.count(("owner", 1)) + gw.messageApproved.count(("owner", 2)) == 2)

    queues["General"].put(send_message("owner", 1, "low"))
    queues["Critical"].put(send_message("owner", 2, "high"))
    # wait until both messages are visible so the priority drain sees them together
    while queues["General"].empty() or queues["Critical"].empty():
        pass

    gw.thread_work()
    pump(gw, lambda: recv.poll())
    assert recv.recv()["value"] == "high"
    pump(gw, lambda: recv.poll())
    assert recv.recv()["value"] == "low"
