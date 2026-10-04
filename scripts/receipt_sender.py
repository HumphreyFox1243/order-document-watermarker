import argparse
import base64
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Watermark a receipt through the local service")
    parser.add_argument("pdf", type=Path, help="Path to the source PDF")
    parser.add_argument("--order", required=True, help="Store order ID")
    parser.add_argument("--customer", required=True, help="Recipient name")
    parser.add_argument("--service-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    response = httpx.request(
        "POST",
        f"{args.service_url}/documents/share",
        json={
            "order_id": args.order,
            "customer_name": args.customer,
            "document_kind": "receipt",
            "pdf": base64.b64encode(args.pdf.read_bytes()).decode("ascii"),
        },
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()
    print(result["watermarked_pdf"])


if __name__ == "__main__":
    main()
