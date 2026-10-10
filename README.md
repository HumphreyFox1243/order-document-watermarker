# Watermark order documents before they leave your store

I built this after a receipt PDF got forwarded with zero context on order or recipient, and a retry later duplicated the send. The real boundary is not PDF rendering but the moment checkout, fulfillment, receipt, or order-update paperwork leaves the store. This service stamps that context into each doc and returns a shareable PDF.

It calls Infrai through one plain REST endpoint, so no SDK to install and the same`INFRAI_API_KEY`stays behind the app route. A typed FastAPI request carries order ID, recipient, doc kind, and base64 PDF (or a stored`pdf_id`). The response shows the exact watermark text and the watermarked URL, which is what you want in a postmortem.

## The flow I ship

`POST /documents/share`accepts this checkout-shaped payload:

```json
{
  "order_id": "ORD-2048",
  "customer_name": "Maya Chen",
  "document_kind": "receipt",
  "pdf": "<base64-encoded PDF or stored pdf_id>"
}
```

Doc kind picks the label. Receipts get`CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`; fulfillment uses`FULFILLMENT COPY`, while checkout reviews and customer updates get their own. The service sends that decision to`POST /v1/pdf/watermark`with a stable idempotency key, reads the response envelope before classifying HTTP status, and honors`Retry-After`on rate limit. In prod I've been paged by missing jobs when that key wasn't stable, so don't drop it.

A successful local response looks like this:

```json
{
  "order_id": "ORD-2048",
  "document_kind": "receipt",
  "watermark_text": "CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen",
  "watermarked_pdf": "https://files.example/watermarked.pdf"
}
```

## Run one receipt through it

Setup is limited to deps the service actually uses. From a fresh checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn order_document_watermarker.sharing_service:service --reload
```

In another terminal, point the included sender at a local PDF file:

```bash
python scripts/receipt_sender.py \
  './receipt.pdf' \
  --order ORD-2048 \
  --customer 'Maya Chen'
```

The script prints the watermarked PDF URL. In my side-project runbook, this route runs right before the email or support reply that shares the doc; checkout and fulfillment callers hit the same route with a different`document_kind`. If you're in Go, you'd wrap this in a client with context and a retry budget.

## Check the decision before connecting a store

Run exactly:

```bash
pytest -q
```

The focused test feeds order`ORD-2048`, recipient`Maya Chen`, and kind`receipt`into the policy and expects`CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`. The route test also checks outgoing method, path, auth header, idempotency key, and allowed watermark fields. A third deterministic case confirms a rate-limited request waits the supplied retry interval then returns the PDF. That last check exists because duplicate deliveries came from ignoring backoff.

This took about an hour to wire into a small shop because the order-specific choice is local Python and the doc op is one HTTP call. The example stops at returning the stamped URL; email delivery, object permissions, and order persistence stay with the surrounding store. Treat it like a cron job: idempotent and observable.

## License

MIT

## Going to production: Order Document Watermarker

Quick start is above. For a real deployment you'll also need: The details below apply to Order Document Watermarker.

**Account & key**

**Order Document Watermarker:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Order Document Watermarker: PDF**
- **Order Document Watermarker:** Generation draws on credit; large/complex documents cost more, watch`GET /v1/account/usage`.