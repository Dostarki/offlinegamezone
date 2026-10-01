import asyncio
import contextlib
import json
import os
import statistics
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
import websockets


def base_url() -> str:
    value = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not value:
        for line in Path("/app/frontend/.env").read_text(encoding="utf-8").splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                value = line.split("=", 1)[1].strip()
                break
    if not value:
        raise RuntimeError("REACT_APP_BACKEND_URL missing")
    return value.rstrip("/")


BASE_URL = base_url()


def ws_url(token: str) -> str:
    parsed = urlparse(BASE_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/api/ws/{token}"


async def join(name: str):
    r = requests.post(f"{BASE_URL}/api/join", json={"name": name, "weapon": "ak47", "skin": "soldier"}, timeout=10)
    r.raise_for_status()
    ws = await websockets.connect(ws_url(r.json()["token"]), open_timeout=8)
    while True:
        m = json.loads(await ws.recv())
        if m.get("type") == "state":
            return ws


async def main():
    clients = []
    tick_ms = []
    rtts = []
    state_count = 0
    ping_marks = {}
    first_seq = None
    first_server_time = None
    last_seq = None
    last_server_time = None

    try:
        suffix = int(time.time()) % 100000
        for i in range(6):
            clients.append(await join(f"RTT{i}{suffix}"))
        collector = clients[0]
        start = time.monotonic()
        next_ping = start

        while time.monotonic() - start < 5:
            now = time.monotonic()
            if now >= next_ping:
                stamp = int(now * 1000)
                ping_marks[stamp] = now
                await collector.send(json.dumps({"type": "ping", "time": stamp}))
                next_ping += 1

            msg = json.loads(await asyncio.wait_for(collector.recv(), timeout=2))
            if msg.get("type") == "state":
                state_count += 1
                tick_ms.append(float(msg.get("tick_ms", 0)))
                if first_seq is None:
                    first_seq = int(msg.get("seq", 0))
                    first_server_time = float(msg.get("server_time", 0))
                last_seq = int(msg.get("seq", 0))
                last_server_time = float(msg.get("server_time", 0))
            elif msg.get("type") == "pong" and msg.get("time") in ping_marks:
                sent = ping_marks.pop(msg["time"])
                rtts.append((time.monotonic() - sent) * 1000)

        if first_seq is not None and last_seq is not None and last_server_time and first_server_time is not None:
            hz = (last_seq - first_seq) / max(0.001, (last_server_time - first_server_time) / 1000)
        else:
            hz = 0.0
        p50 = statistics.median(rtts) if rtts else None
        p95 = statistics.quantiles(rtts, n=100, method='inclusive')[94] if len(rtts) >= 20 else None
        print(
            json.dumps(
                {
                    "states": state_count,
                    "state_hz": round(hz, 2),
                    "rtt_p50_ms": None if p50 is None else round(p50, 2),
                    "rtt_p95_ms": None if p95 is None else round(p95, 2),
                    "rtt_max_ms": round(max(rtts), 2) if rtts else None,
                    "rtt_samples": len(rtts),
                    "tick_mean_ms": round(statistics.mean(tick_ms), 3) if tick_ms else None,
                },
                ensure_ascii=False,
            )
        )
    finally:
        for ws in clients:
            with contextlib.suppress(Exception):
                await ws.close()


if __name__ == "__main__":
    asyncio.run(main())
