"""Vercel Function: receive an enquiry and forward it through Resend."""
import json
import os
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.respond(HTTPStatus.BAD_REQUEST, "Invalid enquiry data.")
            return

        required = ("name", "phone", "message")
        if any(not str(payload.get(field, "")).strip() for field in required):
            self.respond(HTTPStatus.BAD_REQUEST, "Please complete the required fields.")
            return

        api_key = os.environ.get("RESEND_API_KEY", "")
        sender = os.environ.get("RESEND_FROM", "")
        recipient = os.environ.get("RESEND_TO_EMAIL", "")
        if not api_key or not sender or not recipient:
            self.respond(HTTPStatus.SERVICE_UNAVAILABLE, "Email delivery is not configured yet.")
            return

        def value(field):
            return str(payload.get(field, "")).strip()

        def safe(field):
            return escape(value(field))

        html = f"""<h2>New SVS &amp; Co. enquiry</h2>
        <p><strong>Name:</strong> {safe('name')}</p>
        <p><strong>Phone:</strong> {safe('phone')}</p>
        <p><strong>Email:</strong> {safe('email') or 'Not provided'}</p>
        <p><strong>Project type:</strong> {safe('project') or 'Not selected'}</p>
        <p><strong>Location:</strong> {safe('location') or 'Not provided'}</p>
        <p><strong>Message:</strong><br>{safe('message').replace(chr(10), '<br>')}</p>"""
        email = {
            "from": sender,
            "to": [recipient],
            "subject": f"New website enquiry from {value('name')}",
            "html": html,
        }
        if value("email"):
            email["reply_to"] = value("email")

        request = Request(
            "https://api.resend.com/emails",
            data=json.dumps(email).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=15):
                pass
        except HTTPError:
            self.respond(HTTPStatus.BAD_GATEWAY, "Unable to send the enquiry. Please try again shortly.")
            return
        except URLError:
            self.respond(HTTPStatus.SERVICE_UNAVAILABLE, "Email service is unavailable. Please try again shortly.")
            return
        self.respond(HTTPStatus.OK, "Thank you. Your enquiry has been sent to SVS & Co.")

    def do_GET(self):
        self.respond(HTTPStatus.METHOD_NOT_ALLOWED, "Use POST to send an enquiry.")

    def respond(self, status, message):
        body = json.dumps({"message": message}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


