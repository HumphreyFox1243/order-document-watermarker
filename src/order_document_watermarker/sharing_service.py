import os
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException

from .infrai_pdf import InfraiError, InfraiPdfClient
from .order_watermark import (
    ShareDocumentRequest,
    ShareDocumentResult,
    watermark_text_for,
)

service = FastAPI(title="Order document sharing")


def pdf_client() -> InfraiPdfClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return InfraiPdfClient(api_key)


def _output_url(data: dict[str, Any]) -> str:
    for key in ("url", "pdf"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return value
    raise HTTPException(status_code=502, detail="Watermark response did not contain a PDF URL")


@service.post("/documents/share", response_model=ShareDocumentResult)
def share_document(
    request: ShareDocumentRequest,
    client: InfraiPdfClient = Depends(pdf_client),
) -> ShareDocumentResult:
    text = watermark_text_for(request)
    try:
        data = client.watermark(
            pdf=str(request.pdf),
            text=text,
            idempotency_key=f"share:{request.order_id}:{request.document_kind.value}",
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Document service request failed") from exc

    return ShareDocumentResult(
        order_id=request.order_id,
        document_kind=request.document_kind,
        watermark_text=text,
        watermarked_pdf=_output_url(data),
    )

