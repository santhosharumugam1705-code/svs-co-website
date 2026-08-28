"""Local static server with a server-side Resend enquiry endpoint."""
import json
import os
from html import escape
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent


def load_env():
    values = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


CONFIG = load_env()


class AppHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/enquiry":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.handle_enquiry()

    def handle_enquiry(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.respond_json(HTTPStatus.BAD_REQUEST, {"message": "Invalid enquiry data."})
            return

        required = ("name", "phone", "message")
        if any(not str(payload.get(field, "")).strip() for field in required):
            self.respond_json(HTTPStatus.BAD_REQUEST, {"message": "Please complete the required fields."})
            return

        api_key = os.environ.get("RESEND_API_KEY", CONFIG.get("RESEND_API_KEY", ""))
        sender = os.environ.get("RESEND_FROM", CONFIG.get("RESEND_FROM", ""))
        recipient = os.environ.get("RESEND_TO_EMAIL", CONFIG.get("RESEND_TO_EMAIL", ""))
        if not api_key or not sender or not recipient:
            self.respond_json(HTTPStatus.SERVICE_UNAVAILABLE, {"message": "Email delivery is not configured yet. Please set RESEND_FROM and RESEND_TO_EMAIL."})
            return

        def clean(field):
            return str(payload.get(field, "")).strip()

        def safe(field):
            return escape(clean(field))

        html = f"""<h2>New SVS &amp; Co. enquiry</h2>
        <p><strong>Name:</strong> {safe('name')}</p>
        <p><strong>Phone:</strong> {safe('phone')}</p>
        <p><strong>Email:</strong> {safe('email') or 'Not provided'}</p>
        <p><strong>Project type:</strong> {safe('project') or 'Not selected'}</p>
        <p><strong>Location:</strong> {safe('location') or 'Not provided'}</p>
        <p><strong>Message:</strong><br>{safe('message').replace(chr(10), '<br>')}</p>"""
        resend_payload = json.dumps({
            "from": sender,
            "to": [recipient],
            "subject": f"New website enquiry from {clean('name')}",
            "html": html,
            "reply_to": clean("email") or None,
        }).encode("utf-8")
        request = Request("https://api.resend.com/emails", data=resend_payload, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }, method="POST")
        try:
            with urlopen(request, timeout=15):
                pass
        except HTTPError:
            self.respond_json(HTTPStatus.BAD_GATEWAY, {"message": "Unable to send the enquiry. Please try again shortly."})
            return
        except URLError:
            self.respond_json(HTTPStatus.SERVICE_UNAVAILABLE, {"message": "Email service is unavailable. Please try again shortly."})
            return
        self.respond_json(HTTPStatus.OK, {"message": "Thank you. Your enquiry has been sent to SVS & Co."})

    def respond_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    os.chdir(ROOT)
    print("SVS & Co. is running at http://127.0.0.1:4173/")
    ThreadingHTTPServer(("127.0.0.1", 4173), AppHandler).serve_forever()

