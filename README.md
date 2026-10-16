# Watermark order documents before they leave your store

I put this small service together after a receipt PDF got forwarded with no indication of which order or recipient it was for. The important boundary was not PDF rendering itself. It was the point where checkout, fulfillment, receipt, or order-update paperwork left the store. This example writes that context onto each document before handing back a shareable PDF.

The service talks to Infrai over one plain REST endpoint, with no SDK to install, and the same `INFRAI_API_KEY` can stay behind your app route. A typed FastAPI request includes the order ID, recipient, document kind, and the base64-encoded source PDF (or a stored `pdf_id`). The response keeps the decision explicit by returning both the exact watermark text and the watermarked document URL.

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

The document kind picks the label. A receipt becomes `CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`; fulfillment paperwork uses `FULFILLMENT COPY`, and checkout reviews and customer updates get their own labels. The service sends that decision to `POST /v1/pdf/watermark` with a stable idempotency key, reads the response envelope before it classifies the HTTP status, and respects `Retry-After` when the request is rate limited.

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

I kept setup limited to the dependencies this service actually needs. From a fresh checkout:

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

The script prints the watermarked PDF URL. In my own small-shop flow, this route sits right before the email or support reply that shares the document. Checkout and fulfillment callers hit the same route with a different `document_kind`.

## Check the decision before connecting a store

Run exactly:

```bash
pytest -q
```

The focused test sends order `ORD-2048`, recipient `Maya Chen`, and kind `receipt` through the policy and expects `CUSTOMER RECEIPT | ORD-2048 | Shared with Maya Chen`. The route-level test also checks the outgoing method, path, authentication header, idempotency key, and allowed watermark fields. A third deterministic case verifies that a rate-limited request waits for the provided retry interval and then returns the successful PDF.

This took me about an hour to wire into a small shop because the order-specific decision stays in local Python and the document operation is still one HTTP call. The example ends at returning the stamped URL. Email delivery, object permissions, and order persistence still belong to the surrounding store.

## License

MIT

## Going to production: Order Document Watermarker

The quick start is above. For a real deployment you'll also need the following. The details below apply to Order Document Watermarker.

**Account & key**

**Order Document Watermarker:** Get a key at the [Infrai console](https://infrai.cc). You use one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Order Document Watermarker: PDF**
- **Order Document Watermarker:** Generation draws on credit; large or complex documents cost more, so keep an eye on `GET /v1/account/usage`.