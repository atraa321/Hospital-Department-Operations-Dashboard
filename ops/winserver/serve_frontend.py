from __future__ import annotations

import argparse
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


def build_handler(dist_dir: Path):
    class SPAStaticHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist_dir), **kwargs)

        def _serve_index(self) -> None:
            self.path = "/index.html"
            return super().do_GET()

        def do_GET(self):  # noqa: N802
            path = unquote(urlsplit(self.path).path)
            # API requests are not served by this static server.
            if path.startswith("/api/"):
                self.send_error(404, "API route is not hosted on frontend static server")
                return

            local_path = Path(self.translate_path(path))
            if local_path.exists() and not local_path.is_dir():
                return super().do_GET()
            return self._serve_index()

        def do_HEAD(self):  # noqa: N802
            path = unquote(urlsplit(self.path).path)
            local_path = Path(self.translate_path(path))
            if local_path.exists() and not local_path.is_dir():
                return super().do_HEAD()
            self.path = "/index.html"
            return super().do_HEAD()

    return SPAStaticHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve frontend dist with SPA fallback.")
    parser.add_argument("--dist", required=True, help="Frontend dist directory path")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=5173, help="Bind port")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_dir = Path(args.dist).resolve()
    if not dist_dir.exists():
        raise FileNotFoundError(f"dist directory not found: {dist_dir}")
    if not (dist_dir / "index.html").exists():
        raise FileNotFoundError(f"index.html not found in dist directory: {dist_dir}")

    handler = build_handler(dist_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    server.daemon_threads = True

    print(f"[frontend] serving {dist_dir}")
    print(f"[frontend] listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
