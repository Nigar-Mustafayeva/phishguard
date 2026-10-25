"""Application entry point.

Run locally with:  python run.py
In production (Render) Gunicorn imports the `app` object below.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True only affects local development.
    app.run(host="127.0.0.1", port=5000, debug=True)
