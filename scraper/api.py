"""Prosty endpoint Flask zwracający wynik ostatniego skanu.

    GET /scan/latest  -> zawartość last_scan.json (404, jeśli jeszcze nie było skanu)
    GET /health       -> {"status": "ok"}
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify

from . import config


def create_app(last_scan_file: Path | None = None) -> Flask:
    scan_file = Path(last_scan_file or config.LAST_SCAN_FILE)
    app = Flask(__name__)
    app.json.ensure_ascii = False  # polskie znaki bez \uXXXX
    app.json.sort_keys = False

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    @app.get("/scan/latest")
    def latest_scan():
        if not scan_file.exists():
            return jsonify(blad="Brak skanu — skraper jeszcze nic nie zapisał"), 404
        # Plik jest zapisywany atomowo, więc oddajemy go bez ponownego parsowania.
        resp = Response(scan_file.read_bytes(), mimetype="application/json")
        modified = datetime.fromtimestamp(scan_file.stat().st_mtime, tz=timezone.utc)
        resp.headers["Last-Modified"] = modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    return app


# Obiekt dla gunicorna: gunicorn scraper.api:app
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
