"""Standard-library local web server for the Netbone web app."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any
from urllib.parse import urlparse

from netbone.exceptions import NetboneError, ValidationError
from netbone.webapp.bridge import (
    _Download,
    comparison_payload,
    error_payload,
    experiment_export_payload,
    filter_payload,
    filter_preview_payload,
    graph_export_payload,
    preview_payload,
    registry_payload,
    result_export_payload,
    run_pipeline_from_payload,
    score_payload,
    sweep_payload,
    ui_schema_payload,
)

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_MAX_UPLOAD_MB = 100
ASSET_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "app.js": "application/javascript; charset=utf-8",
}


def _invalid_json_payload(error: json.JSONDecodeError) -> Mapping[str, object]:
    return error_payload(
        ValidationError(
            f"Request body is not valid JSON ({error.msg} at line {error.lineno}, "
            f"column {error.colno})."
        )
    )


class PayloadTooLargeError(ValidationError):
    """Raised when a request body is larger than the server accepts."""


def run(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    max_upload_mb: float = DEFAULT_MAX_UPLOAD_MB,
) -> None:
    """Serve the local Netbone web app until interrupted.

    Args:
        host: Interface to bind.
        port: TCP port to listen on.
        max_upload_mb: Largest request body accepted, in megabytes. Larger
            uploads get a 413 response instead of being read into memory.
    """

    if not max_upload_mb > 0:
        raise ValueError("max_upload_mb must be positive.")
    handler = type(
        "ConfiguredNetboneWebHandler",
        (NetboneWebHandler,),
        {"max_body_bytes": int(max_upload_mb * 1024 * 1024)},
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Netbone web app running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Netbone web app.")
    finally:
        server.server_close()


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    """Run the local web server from the command line."""

    parser = argparse.ArgumentParser(
        prog=prog, description="Run the local Netbone web app."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument(
        "--max-upload-mb",
        default=DEFAULT_MAX_UPLOAD_MB,
        type=float,
        help=f"Largest upload accepted, in MB (default {DEFAULT_MAX_UPLOAD_MB}).",
    )
    args = parser.parse_args(argv)
    if args.max_upload_mb <= 0:
        parser.error("--max-upload-mb must be positive.")
    run(host=args.host, port=args.port, max_upload_mb=args.max_upload_mb)
    return 0


class NetboneWebHandler(BaseHTTPRequestHandler):
    """HTTP handler for static assets and Netbone API requests."""

    server_version = "NetboneWeb/0.1"
    max_body_bytes = DEFAULT_MAX_UPLOAD_MB * 1024 * 1024

    def do_GET(self) -> None:
        """Serve the app shell or registry metadata."""

        if not self._host_allowed():
            self.send_error(HTTPStatus.FORBIDDEN, "Unexpected Host header.")
            return
        path = urlparse(self.path).path
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/api/ui-schema":
            self._write_json(HTTPStatus.OK, ui_schema_payload())
            return
        if path == "/api/registry":
            self._write_json(HTTPStatus.OK, registry_payload())
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        """Run a web pipeline request."""

        if not self._host_allowed() or not self._same_origin():
            self._write_json(
                HTTPStatus.FORBIDDEN,
                {
                    "status": "error",
                    "error": "Forbidden",
                    "message": (
                        "Cross-origin requests to the Netbone web app are not allowed."
                    ),
                },
            )
            return
        path = urlparse(self.path).path
        if path == "/api/preview":
            self._handle_json_request(preview_payload)
            return
        if path == "/api/score":
            self._handle_json_request(score_payload)
            return
        if path == "/api/filter":
            self._handle_json_request(filter_payload)
            return
        if path == "/api/filter-preview":
            self._handle_json_request(filter_preview_payload)
            return
        if path == "/api/compare":
            self._handle_json_request(comparison_payload)
            return
        if path == "/api/sweep":
            self._handle_json_request(sweep_payload)
            return
        if path == "/api/export":
            self._handle_download_request(graph_export_payload)
            return
        if path == "/api/export-result":
            self._handle_download_request(result_export_payload)
            return
        if path == "/api/export-experiment":
            self._handle_download_request(experiment_export_payload)
            return
        if path == "/api/run":
            self._handle_json_request(run_pipeline_from_payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_json_request(
        self,
        handler: Any,
    ) -> None:
        try:
            payload = self._read_json()
            result = handler(payload)
        except PayloadTooLargeError as exc:
            self.close_connection = True
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error_payload(exc))
            return
        except NetboneError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, error_payload(exc))
            return
        except json.JSONDecodeError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, _invalid_json_payload(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, error_payload(exc))
            return

        self._write_json(HTTPStatus.OK, result)

    def _handle_download_request(self, handler: Callable[[object], _Download]) -> None:
        try:
            payload = self._read_json()
            export = handler(payload)
        except PayloadTooLargeError as exc:
            self.close_connection = True
            self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, error_payload(exc))
            return
        except NetboneError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, error_payload(exc))
            return
        except json.JSONDecodeError as exc:
            self._write_json(HTTPStatus.BAD_REQUEST, _invalid_json_payload(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            self._write_json(HTTPStatus.INTERNAL_SERVER_ERROR, error_payload(exc))
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", export.content_type)
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{export.filename}"',
        )
        self.send_header("Content-Length", str(len(export.content)))
        self.end_headers()
        self.wfile.write(export.content)

    def _request_host(self) -> str:
        return (self.headers.get("Host") or "").strip().lower()

    def _host_allowed(self) -> bool:
        """Reject DNS-rebinding requests when the server listens on loopback."""

        address = self.server.server_address
        bound_host = str(address[0] if isinstance(address, tuple) else address)
        bound_host = bound_host.lower()
        if bound_host not in LOOPBACK_HOSTS:
            return True
        host = self._request_host()
        if not host:
            return False
        hostname = urlparse(f"http://{host}").hostname or ""
        return hostname in LOOPBACK_HOSTS

    def _same_origin(self) -> bool:
        """Reject browser requests sent by another website."""

        origin = self.headers.get("Origin")
        if origin is None or origin == "null":
            return origin is None
        return urlparse(origin).netloc.lower() == self._request_host()

    def log_message(self, format: str, *args: object) -> None:
        """Keep local server output focused on startup and fatal errors."""

    def _serve_static(self, path: str) -> None:
        asset_name = "index.html" if path in {"", "/"} else path.lstrip("/")
        if asset_name not in ASSET_TYPES:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            asset = resources.files("netbone.webapp").joinpath("static", asset_name)
        except ModuleNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            body = asset.read_bytes()
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ASSET_TYPES[asset_name])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Mapping[str, object]:
        length_text = self.headers.get("Content-Length")
        if length_text is None:
            raise ValidationError("Request is missing Content-Length.")
        try:
            length = int(length_text)
        except ValueError as exc:
            raise ValidationError("Request Content-Length must be an integer.") from exc
        if length < 0:
            raise ValidationError("Request Content-Length cannot be negative.")
        if length > self.max_body_bytes:
            limit_mb = self.max_body_bytes / (1024 * 1024)
            raise PayloadTooLargeError(
                f"The upload is {length / (1024 * 1024):.1f} MB, larger than the "
                f"{limit_mb:g} MB limit. Restart the app with a higher "
                "--max-upload-mb to load it."
            )
        raw_body = self.rfile.read(length)
        try:
            text = raw_body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("Request body must be UTF-8 encoded JSON.") from exc
        decoded = json.loads(text)
        if not isinstance(decoded, Mapping):
            raise ValidationError("Request body must contain a JSON object.")
        return decoded

    def _write_json(
        self,
        status: HTTPStatus,
        payload: Mapping[str, Any],
    ) -> None:
        body = (
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
