from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.brokers.services.connections.queue.amazon_sqs_connection_service import (
    AmazonSQSConnectionService,
)
from exceptions.app_exception import QsmithAppException


def test_ack_messages_returns_deleted_messages_when_all_delete_succeed(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    monkeypatch.setattr(service, "test_connection", lambda _config, _queue_id: (sqs, "queue-url"))
    messages = [
        {"MessageId": "m1", "ReceiptHandle": "rh1"},
        {"MessageId": "m2", "ReceiptHandle": "rh2"},
    ]

    result = service.ack_messages(None, "queue-id", messages)

    assert result == [
        {"status": "ok", "message_id": "m1"},
        {"status": "ok", "message_id": "m2"},
    ]
    assert sqs.delete_message.call_count == 2


def test_ack_messages_raises_on_partial_delete_failures(monkeypatch):
    service = AmazonSQSConnectionService()
    sqs = MagicMock()
    sqs.delete_message.side_effect = [
        None,
        ClientError(
            {
                "Error": {
                    "Code": "ReceiptHandleIsInvalid",
                    "Message": "The input receipt handle is invalid.",
                }
            },
            "DeleteMessage",
        ),
    ]
    monkeypatch.setattr(service, "test_connection", lambda _config, _queue_id: (sqs, "queue-url"))
    messages = [
        {"MessageId": "m1", "ReceiptHandle": "rh1"},
        {"MessageId": "m2", "ReceiptHandle": "rh2"},
    ]

    with pytest.raises(QsmithAppException) as exc_info:
        service.ack_messages(None, "queue-id", messages)

    error_message = str(exc_info.value)
    assert "ACK failed for 1 of 2 message(s)." in error_message
    assert "Deleted=1" in error_message
    assert "m2" in error_message
