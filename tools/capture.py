"""mitmproxy addon that captures whoop API traffic to a log file.

usage:
    /home/deck/mitmproxy-env/bin/mitmproxy -s tools/capture.py --listen-port 8080

then point your phone's wifi proxy to your steam deck IP on port 8080.
browse to mitm.it on your phone to install the CA certificate.
open the whoop app and perform actions — captured requests appear in
tools/captured_endpoints.log
"""
import json
from datetime import datetime, timezone
from mitmproxy import http

LOG_FILE = "tools/captured_endpoints.log"
WHOOP_HOSTS = ["api.prod.whoop.com", "api-7.whoop.com"]


def response(flow: http.HTTPFlow) -> None:
    if not any(host in (flow.request.host or "") for host in WHOOP_HOSTS):
        return

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "path": flow.request.path,
        "status": flow.response.status_code if flow.response else None,
        "request_headers": dict(flow.request.headers),
        "response_headers": dict(flow.response.headers) if flow.response else {},
    }

    # capture request body
    if flow.request.content:
        try:
            entry["request_body"] = json.loads(flow.request.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            entry["request_body"] = flow.request.content.decode("utf-8", errors="replace")

    # capture response body
    if flow.response and flow.response.content:
        try:
            entry["response_body"] = json.loads(flow.response.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            entry["response_body"] = flow.response.content.decode("utf-8", errors="replace")

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, indent=2, default=str) + "\n---\n")

    # print summary to mitmproxy console
    print(
        f"[whoop] {entry['method']} {entry['path']} "
        f"-> {entry['status']}"
    )
