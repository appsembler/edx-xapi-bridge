import http.server
import socketserver

from xapi_bridge import settings


class StatusOKRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        """Respond to any request with a basic 'OK' status, for uptime monitoring.
        """
        self.send_response(200, 'OK')
        self.send_header('Content-type', 'text/html')
        self.end_headers()


httpd = socketserver.TCPServer((
    getattr(settings, 'HTTP_PUBLISH_IP', '0.0.0.0'),
    getattr(settings, 'HTTP_PUBLISH_PORT', 9090)),
    StatusOKRequestHandler)
