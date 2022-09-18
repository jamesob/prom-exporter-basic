#!/usr/bin/env python3

import subprocess
import argparse
import threading
import sys
import shutil
import contextlib
import socket
import logging
from io import BytesIO

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)
logging.basicConfig()


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET commands."""
    server_version = "SimpleHTTP/1.0"

    def do_GET(self):
        """Serve a GET request."""
        content: str = self.get_content()
        f = BytesIO()
        f.write(content.encode('utf-8'))
        f.seek(0)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", 'text')
        self.send_header("Content-Length", str(len(f.getbuffer())))
        self.end_headers()

        shutil.copyfileobj(f, self.wfile)

    def get_content(self) -> str:
        raise NotImplementedError


# ensure dual-stack is not disabled; ref #38907
class Server(ThreadingHTTPServer):

    def server_bind(self):
        # suppress exception when protocol is IPv4
        with contextlib.suppress(Exception):
            self.socket.setsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self)


def run_server(
        bind='127.0.0.1', port=8000,
        HandlerClass=BaseHTTPRequestHandler,
        protocol="HTTP/1.0"
):
    """Run the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the port argument).

    """
    infos = socket.getaddrinfo(
        bind, port,
        type=socket.SOCK_STREAM,
        flags=socket.AI_PASSIVE,
    )
    Server.address_family, _, _, _, addr = next(iter(infos))
    HandlerClass.protocol_version = protocol

    with Server(addr, HandlerClass) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f'[{host}]' if ':' in host else host
        print(
            f"Serving HTTP on {host} port {port} "
            f"(http://{url_host}:{port}/) ..."
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


class MyReqHandler(SimpleHTTPRequestHandler):

    def get_content(self):
        return server_info()


net_lock = threading.Lock()
net_measurements = {}
net_poller = None


class IfstatPoller(threading.Thread):

    def run(self):
        popen = subprocess.Popen('ifstat', text=True, stdout=subprocess.PIPE)
        assert popen.stdout
        devices = popen.stdout.readline().split()
        # Skip the metric name column
        popen.stdout.readline()

        while (line := popen.stdout.readline()):
            inouts = line.split()
            try:
                assert len(inouts) == len(devices) * 2

                with net_lock:
                    for i, d in enumerate(devices):
                        net_measurements[d] = inouts[2 * i:(2 * i) + 2]
            except Exception:
                logging.exception("failed to get network stats")
                with net_lock:
                    net_measurements.clear()


def server_info() -> str:
    output = []

    def ao(line):
        output.append(line)

    hostname = socket.gethostname()
    df_lines = stdout('df | grep -v tmpfs').splitlines()[1:]

    for line in df_lines:
        dev, _, used, avail, useperc, mount = line.split()
        useperc = useperc.strip('%')
        ao(f"disk_bytes_used{{host={hostname},mount={mount},device={dev}}} {used}")
        ao(f"disk_bytes_avail{{host={hostname},mount={mount},device={dev}}} {avail}")
        ao(f"disk_used_percent{{host={hostname},mount={mount},device={dev}}} {useperc}")

    load1, load5, load15 = stdout('cat /proc/loadavg').split()[:3]

    ao(f"cpu_load_1min{{host={hostname}}} {load1}")
    ao(f"cpu_load_5min{{host={hostname}}} {load5}")
    ao(f"cpu_load_15min{{host={hostname}}} {load15}")

    if net_poller:
        with net_lock:
            for dev, (inkb, outkb) in net_measurements.items():
                ao(f"net_KB_in{{host={hostname},device={dev}}} {inkb}")
                ao(f"net_KB_out{{host={hostname},device={dev}}} {outkb}")

    return '\n'.join(output)


def stdout(cmd) -> str:
    return subprocess.run(cmd, shell=True, text=True, capture_output=True).stdout


def main():
    global net_poller

    parser = argparse.ArgumentParser(description='basic system metrics for prometheus')
    parser.add_argument('-p', '--port', type=int, default=8000)
    parser.add_argument('-b', '--bind', default='0.0.0.0')
    args = parser.parse_args()

    if subprocess.run('which ifstat', capture_output=True, shell=True).returncode == 0:
        net_poller = IfstatPoller()
        net_poller.start()

    run_server(args.bind, port=args.port, HandlerClass=MyReqHandler)


if __name__ == "__main__":
    main()
