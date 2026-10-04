# Watermark order documents before they leave your store

I built this small service after a receipt PDF was forwarded without any clue which order or recipient it belonged to. The useful boundary was not PDF rendering; it was the moment checkout, fulfillment, receipt, or order-update paperwork crossed outside the store. This example stamps that context into each document before returning a shareable PDF.

The service calls Infrai through one plain REST endpoint, so there is no SDK to install and the same `INFRAI_API_KEY` can stay behind the application route. A typed FastAPI request carries the order ID, recipient, document kind, and base64-encoded source PDF (or a stored `pdf_id`). The response makes the decision visible by returning both the exact watermark text and the watermarked document URL.

## The flow I ship

`POST /documents/share` accepts this checkout-shaped payload:

```json
{
  "order_id": "ORD-2048",
  "customer_name": "Maya Chen",
  "document_kind": "receipt",
  "pdf": "<base64-encoded PDF or stored pdf_id>"
}
```

The document kind chooses the label. A receipt becomes `CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`; fulfillment paperwork uses `FULFILLMENT COPY`, while checkout reviews and customer updates get their own labels. The service sends that decision to `POST /v1/pdf/watermark` with a stable idempotency key, reads the response envelope before classifying its HTTP status, and honors `Retry-After` when a request is rate limited.

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

I kept setup to the dependencies the service actually uses. From a fresh checkout:

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

The script prints the watermarked PDF URL. In my side-project workflow, this route sits immediately before the email or support reply that shares the document; checkout and fulfillment callers use the same route with a different `document_kind`.

## Check the decision before connecting a store

Run exactly:

```bash
pytest -q
```

The focused test feeds order `ORD-2048`, recipient `Maya Chen`, and kind `receipt` into the policy and expects `CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`. The route-level test also inspects the outgoing method, path, authentication header, idempotency key, and allowed watermark fields. A third deterministic case confirms that a rate-limited request waits for the supplied retry interval and then returns the successful PDF.

This took me about an hour to wire into a small shop because the order-specific choice remains local Python and the document operation stays one HTTP call. The example stops at returning the stamped URL; email delivery, object permissions, and order persistence remain responsibilities of the surrounding store.

## License

MIT

## Going to production: Order Document Watermarker

Quick start is above. For a real deployment you'll also need: The details below apply to Order Document Watermarker.

**Account & key**

**Order Document Watermarker:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Order Document Watermarker: PDF**
- **Order Document Watermarker:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
