"""Local-only HTTP surface for Privilege.

The browser is a local operator view. Raw document text is never exposed by a
read API; the page holds the text supplied during its local import action.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import parse_qs, urlparse

from .intake import DocumentExtractionError, ensure_supported, extract_text
from .service import PrivilegeService
from .store import DEFAULT_DB_PATH, VaultStore


WEB_ROOT = Path(__file__).resolve().parents[1] / "web"


class PrivilegeHandler(BaseHTTPRequestHandler):
    service: PrivilegeService

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        try:
            if parsed.path in {"/", "/index.html"}:
                self._send_bytes(WEB_ROOT.joinpath("index.html").read_bytes(), "text/html; charset=utf-8")
            elif parsed.path == "/api/status":
                engagement_id = _query_value(parsed.query, "engagement")
                self._send_json(self.service.status(engagement_id))
            elif parsed.path == "/api/documents":
                self._send_json(self.service.list_documents(_query_value(parsed.query, "engagement")))
            elif parsed.path == "/api/receipts":
                self._send_json(self.service.list_receipts(_query_value(parsed.query, "engagement")))
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._body()
            if self.path == "/api/engagements":
                self._send_json({"engagement_id": self.service.create_engagement(body["name"], body["policy"])}, HTTPStatus.CREATED)
            elif self.path == "/api/documents":
                document_id = self.service.import_document(body["engagement_id"], body["title"], body["raw_text"])
                self._send_json({"document_id": document_id}, HTTPStatus.CREATED)
            elif self.path == "/api/upload":
                # The browser sends bytes; extraction still happens here, on
                # this machine. Nothing is forwarded anywhere.
                text = self._extract_upload(body["filename"], body["content_base64"])
                document_id = self.service.import_document(body["engagement_id"], body["filename"], text)
                self._send_json({"document_id": document_id, "raw_text": text}, HTTPStatus.CREATED)
            elif self.path == "/api/preflight":
                result = self.service.preflight(body["engagement_id"], body["document_id"], body["task"])
                self._send_json(asdict(result))
            elif self.path == "/api/analyze":
                preflight = self.service.preflight(body["engagement_id"], body["document_id"], body["task"])
                analysis = self.service.analyze(preflight)
                self._send_json({"preflight": asdict(preflight), "analysis": asdict(analysis)})
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        """Keep local operator output focused on explicit startup messages."""

    def _body(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length))

    @staticmethod
    def _extract_upload(filename: str, content_base64: str) -> str:
        """Write the upload to a temp file, extract locally, then delete it."""
        suffix = ensure_supported(filename)
        try:
            raw = base64.b64decode(content_base64, validate=True)
        except Exception as error:
            raise DocumentExtractionError("upload was not valid base64") from error

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(raw)
            temporary = Path(handle.name)
        try:
            return extract_text(temporary)
        except (DocumentExtractionError, ValueError) as error:
            # Report the operator's filename, never the temporary path.
            detail = str(error).replace(str(temporary), filename).replace(temporary.name, filename)
            raise DocumentExtractionError(detail) from error
        finally:
            temporary.unlink(missing_ok=True)

    def _send_json(self, data: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_bytes(json.dumps(data, indent=2).encode(), "application/json; charset=utf-8", status)

    def _send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _query_value(query: str, name: str) -> str:
    value = parse_qs(query).get(name, [None])[0]
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing query parameter: {name}")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Privilege web UI")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--port", type=int, default=7077)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    if args.mock:
        os.environ["PRIVILEGE_MOCK"] = "1"
    elif args.live:
        os.environ.pop("PRIVILEGE_MOCK", None)
    PrivilegeHandler.service = PrivilegeService(VaultStore(args.db))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PrivilegeHandler)
    print(f"Privilege local UI: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        PrivilegeHandler.service.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
