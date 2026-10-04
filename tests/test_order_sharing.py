import httpx
from fastapi.testclient import TestClient

from order_document_watermarker.infrai_pdf import InfraiPdfClient
from order_document_watermarker.order_watermark import (
    DocumentKind,
    ShareDocumentRequest,
    watermark_text_for,
)
from order_document_watermarker.sharing_service import pdf_client, service


def test_receipt_watermark_records_order_and_recipient() -> None:
    request = ShareDocumentRequest(
        order_id="ORD-2048",
        customer_name="Maya Chen",
        document_kind=DocumentKind.RECEIPT,
        pdf="JVBERi0xLjQK",
    )

    assert watermark_text_for(request) == (
        "CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen"
    )


def test_share_route_sends_the_expected_watermark_request() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["authorization"] = request.headers["Authorization"]
        seen["idempotency_key"] = request.headers["Idempotency-Key"]
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"url": "https://files.example/watermarked.pdf"},
                "error": None,
                "metadata": {},
            },
        )

    transport = httpx.MockTransport(handler)
    infrai_client = InfraiPdfClient(
        "test-key",
        client=httpx.Client(transport=transport),
        sleep=lambda _: None,
    )
    service.dependency_overrides[pdf_client] = lambda: infrai_client

    try:
        response = TestClient(service).post(
            "/documents/share",
            json={
                "order_id": "ORD-2048",
                "customer_name": "Maya Chen",
                "document_kind": "fulfillment",
                "pdf": "JVBERi0xLjQK",
            },
        )
    finally:
        service.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "order_id": "ORD-2048",
        "document_kind": "fulfillment",
        "watermark_text": "FULFILLMENT COPY | ORD-2048 | Shared with Maya Chen",
        "watermarked_pdf": "https://files.example/watermarked.pdf",
    }
    assert seen == {
        "method": "POST",
        "path": "/v1/pdf/watermark",
        "authorization": "Bearer test-key",
        "idempotency_key": "share:ORD-2048:fulfillment",
        "body": (
            '{"pdf":"JVBERi0xLjQK","text":'
            '"FULFILLMENT COPY | ORD-2048 | Shared with Maya Chen",'
            '"opacity":0.22,"position":"center"}'
        ),
    }


def test_rate_limit_honors_retry_after() -> None:
    sleeps: list[float] = []
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "3"},
                json={
                    "ok": False,
                    "data": None,
                    "error": {"code": "RATE_LIMITED", "message": "Please retry"},
                    "metadata": {},
                },
            )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"url": "https://files.example/final.pdf"},
                "error": None,
                "metadata": {},
            },
        )

    client = InfraiPdfClient(
        "test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=sleeps.append,
    )
    data = client.watermark(
        pdf="JVBERi0xLjQK",
        text="CUSTOMER RECEIPT | ORD-9 | Shared with Jo",
        idempotency_key="share:ORD-9:receipt",
    )

    assert data == {"url": "https://files.example/final.pdf"}
    assert calls == 2
    assert sleeps == [3.0]
