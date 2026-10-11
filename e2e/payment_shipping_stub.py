"""Stand-ins for Razorpay's and Shiprocket's servers, used only by the end-to-end tests.

    python e2e/payment_shipping_stub.py   # listens on :8090

Razorpay:   POST /razorpay/orders                     -> {"id": "order_..."}
Shiprocket: POST /shiprocket/auth/login, /orders/create/adhoc, /courier/assign/awb
            GET  /shiprocket/courier/track/awb/{awb}
"""

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRACKING = {
    "track_url": "https://shiprocket.co/tracking/",
    "shipment_track_activities": [
        {"date": "Today, 18:40", "activity": "In transit", "location": "Bengaluru hub"},
        {"date": "Today, 11:02", "activity": "Picked up by Delhivery", "location": "Mumbai"},
    ],
}


class Stub(BaseHTTPRequestHandler):
    def _reply(self, status: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/razorpay/orders":
            return self._reply(200, {"id": f"order_{secrets.token_hex(7)}", **body})
        if self.path == "/shiprocket/auth/login":
            return self._reply(200, {"token": "e2e-token"})
        if self.path == "/shiprocket/orders/create/adhoc":
            return self._reply(200, {"order_id": 900001, "shipment_id": 900002})
        if self.path == "/shiprocket/courier/assign/awb":
            awb = f"E2E{secrets.randbelow(10**9):09d}"  # unique per shipment, like the real AWBs
            return self._reply(200, {"response": {"data": {"awb_code": awb, "courier_name": "Delhivery"}}})
        self._reply(404, {"error": self.path})

    def do_GET(self) -> None:
        if self.path.startswith("/shiprocket/courier/track/awb/"):
            return self._reply(200, {"tracking_data": TRACKING})
        if self.path == "/health":
            return self._reply(200, {"status": "ok"})
        self._reply(404, {"error": self.path})

    def log_message(self, *_: object) -> None:
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8090), Stub).serve_forever()
