import asyncio
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import websockets


def base_url():
    value = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not value:
        for line in Path('/app/frontend/.env').read_text(encoding='utf-8').splitlines():
            if line.startswith('REACT_APP_BACKEND_URL='):
                value = line.split('=', 1)[1].strip()
                break
    return value.rstrip('/')


def ws_url(token):
    parsed = urlparse(base_url())
    return f"{'wss' if parsed.scheme == 'https' else 'ws'}://{parsed.netloc}/api/ws/{token}"


async def main():
    r = requests.post(f"{base_url()}/api/join", json={"name": f"Hz{int(time.time())%10000}", "weapon": "ak47", "skin": "soldier"}, timeout=10)
    r.raise_for_status()
    ws = await websockets.connect(ws_url(r.json()['token']), open_timeout=8)
    try:
        first = None
        start = time.monotonic()
        while time.monotonic() - start < 5.0:
            m = json.loads(await ws.recv())
            if m.get('type') != 'state':
                continue
            if first is None:
                first = m
            last = m
        elapsed = 5.0
        seq_rate = (last['seq'] - first['seq']) / elapsed
        srv_rate = (last['seq'] - first['seq']) / max(0.001, ((last['server_time'] - first['server_time']) / 1000.0))
        print({"seq_delta": last['seq'] - first['seq'], "seq_rate_hz_wall": round(seq_rate, 2), "seq_rate_hz_server_time": round(srv_rate, 2)})
    finally:
        await ws.close()


if __name__ == '__main__':
    asyncio.run(main())
