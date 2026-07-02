from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import webbrowser

from giflet_core import DEFAULT_OUTPUT_DIR, ExtractionResult, extract_gif_from_bytes, extract_gif_from_url


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web" if (ROOT / "web").is_dir() else Path(sys.prefix) / "web"
EXPORT_DIR = DEFAULT_OUTPUT_DIR


def result_to_json(result: ExtractionResult) -> dict[str, object]:
    return {
        "source": result.source,
        "gif": result.gif_path.name,
        "original": result.original_path.name,
        "width": result.width,
        "height": result.height,
        "frames": result.frames,
        "bytes": result.gif_bytes,
        "previewUrl": f"/exports/{result.gif_path.name}",
        "downloadUrl": f"/exports/{result.gif_path.name}",
    }


class ExtractorRequestHandler(SimpleHTTPRequestHandler):
    server_version = "Giflet/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_file(WEB_ROOT / "index.html")
            return
        if parsed.path.startswith("/assets/"):
            self._send_file(WEB_ROOT / parsed.path.removeprefix("/assets/"))
            return
        if parsed.path.startswith("/exports/"):
            name = Path(unquote(parsed.path.removeprefix("/exports/"))).name
            self._send_file(EXPORT_DIR / name)
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/convert-url":
                self._convert_url()
                return
            if parsed.path == "/api/convert-file":
                self._convert_file()
                return
            self.send_error(404, "Not found")
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _convert_url(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            payload = json.loads(body or "{}")
            url = str(payload.get("url", "")).strip()
        else:
            url = parse_qs(body).get("url", [""])[0].strip()
        if not url:
            raise ValueError("Paste an image URL first.")
        result = extract_gif_from_url(url, EXPORT_DIR)
        self._send_json({"ok": True, "result": result_to_json(result)})

    def _convert_file(self) -> None:
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            },
        )
        file_item = form["image"] if "image" in form else None
        if file_item is None or not getattr(file_item, "filename", ""):
            raise ValueError("Choose an image file first.")
        data = file_item.file.read()
        if not data:
            raise ValueError("The uploaded image is empty.")
        result = extract_gif_from_bytes(data, file_item.filename, EXPORT_DIR)
        self._send_json({"ok": True, "result": result_to_json(result)})

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self.send_error(404, "Not found")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local AWebP GIF extractor web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), ExtractorRequestHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"Serving {url}")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
