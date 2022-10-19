#!/usr/bin/env python3

import subprocess
import argparse
import time
import threading
import logging
from wsgiref.simple_server import make_server


log = logging.getLogger(__name__)
logging.basicConfig()


def wsgi_app(_, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
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
            except AssertionError:
                time.sleep(0.1)
                continue

            try:
                with net_lock:
                    for i, d in enumerate(devices):
                        net_measurements[d] = inouts[2 * i:(2 * i) + 2]
            except Exception:
                logging.exception("failed to get network stats")
                with net_lock:
                    net_measurements.clear()

            time.sleep(0.1)


def server_info() -> list[bytes]:
    output = []

    def ao(line):
        output.append(line.encode() + b'\n')

    df_lines = stdout('df | grep -v tmpfs').splitlines()[1:]

    for line in df_lines:
        dev, _, used, avail, useperc, mount = line.split()
        useperc = useperc.strip('%')
        ao(f'disk_bytes_used{{mount="{mount}",device="{dev}"}} {used}')
        ao(f'disk_bytes_avail{{mount="{mount}",device="{dev}"}} {avail}')
        ao(f'disk_used_percent{{mount="{mount}",device="{dev}"}} {useperc}')

    load1, load5, load15 = stdout('cat /proc/loadavg').split()[:3]

    ao(f"cpu_load_1min {load1}")
    ao(f"cpu_load_5min {load5}")
    ao(f"cpu_load_15min {load15}")

    total, used, free, *_ = stdout('free -m | tail +2').splitlines()[0].split()[1:]

    ao(f"mem_total_mb {total}")
    ao(f"mem_used_mb {used}")
    ao(f"mem_free_mb {free}")
    ao(f"mem_used_perc {int(used) * 100 / int(total):.3f}")

    if net_poller:
        with net_lock:
            for dev, (inkb, outkb) in net_measurements.items():
                try:
                    # Sometimes ifstat reports "n/a"
                    float(inkb)
                    float(outkb)
                except ValueError:
                    pass
                else:
                    ao(f'net_KB_in{{device="{dev}"}} {inkb}')
                    ao(f'net_KB_out{{device="{dev}"}} {outkb}')

    return output


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

    with make_server(args.bind, args.port, wsgi_app) as httpd:
        print(f"serving on {args.bind}:{args.port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
