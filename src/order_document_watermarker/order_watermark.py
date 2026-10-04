from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentKind(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    CUSTOMER_UPDATE = "customer_update"


class ShareDocumentRequest(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    customer_name: str = Field(min_length=1, max_length=120)
    document_kind: DocumentKind
    pdf: str = Field(min_length=1, description="Base64-encoded PDF or stored pdf_id")


class ShareDocumentResult(BaseModel):
    order_id: str
    document_kind: DocumentKind
    watermark_text: str
    watermarked_pdf: str


_LABELS = {
    DocumentKind.CHECKOUT: "CHECKOUT REVIEW",
    DocumentKind.FULFILLMENT: "FULFILLMENT COPY",
    DocumentKind.RECEIPT: "CUSTOMER RECEIPT",
    DocumentKind.CUSTOMER_UPDATE: "ORDER UPDATE",
}


def watermark_text_for(request: ShareDocumentRequest) -> str:
    """Make the sharing context visible when the PDF leaves the store."""
    label = _LABELS[request.document_kind]
    return f"{label} | {request.order_id} | Shared with {request.customer_name}"
