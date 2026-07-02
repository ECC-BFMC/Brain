"""Unit tests for the gateway message router (threadGateway).

The gateway is the process message bus: subscribers register a pipe for an
(Owner, msgID) pair, and send() fans a message out to every registered pipe.
This is the counterpart to the messageHandler tests and is exercised end-to-end
with real pipes.
"""

from multiprocessing import Pipe

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
