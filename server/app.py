"""MotorGuard server. Run: uvicorn app:app --host 0.0.0.0 --port 8000   (from the server/ folder)
Nodes POST feature windows to /ingest. The server learns each node's healthy baseline first, then
classifies, smooths with 3-window voting, estimates time-to-failure, and pushes updates over WebSocket."""
import asyncio, json, os, time
from collections import deque
import numpy as np
import requests
import xgboost as xgb
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
from pydantic import BaseModel
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml"))
import features as F

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "model")
META = json.load(open(os.path.join(MODEL_DIR, "meta.json")))
BOOSTER = xgb.Booster(); BOOSTER.load_model(os.path.join(MODEL_DIR, "motorguard.json"))
CLASSES = META["classes"]
BASELINE_WINDOWS = int(os.environ.get("BASELINE_WINDOWS", 30))  # real deployment: ~24 h of windows
VOTES = int(os.environ.get("VOTES", 3))
TG_TOKEN, TG_CHAT = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
FAIL_AT = 0.8  # fault probability that we call "failure" for time-to-failure extrapolation

app = FastAPI(title="MotorGuard")
nodes, clients = {}, set()


class Window(BaseModel):
    node_id: str
    ts: Optional[float] = None
    rms: float; crest: float; kurt: float; f_run: float
    a1x: float; a2x: float; a3x: float; r21: float
    e_low: float; e_mid: float; e_high: float; centroid: float
    cur_rms: float; temp: float


def node_state(nid):
    return nodes.setdefault(nid, dict(base_rows=[], base=None, hist=deque(maxlen=300), votes=deque(maxlen=VOTES), alerted=False, status="learning"))


def ttf_seconds(hist):
    """Linear extrapolation of recent fault probability to FAIL_AT. Returns None if not rising."""
    pts = [(t, p) for t, p in list(hist)[-40:]]
    if len(pts) < 10:
        return None
    t = np.array([p[0] for p in pts]); p = np.array([p[1] for p in pts])
    slope, icpt = np.polyfit(t - t[0], p, 1)
    if slope <= 1e-5 or p[-1] >= FAIL_AT:
        return None
    return float((FAIL_AT - p[-1]) / slope)


def notify(text):
    print("ALERT:", text)
    if TG_TOKEN and TG_CHAT:
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json=dict(chat_id=TG_CHAT, text=text), timeout=5)
        except Exception as e:
            print("telegram failed", e)


async def broadcast(msg):
    for c in list(clients):
        try:
            await c.send_text(json.dumps(msg))
        except Exception:
            clients.discard(c)


@app.post("/ingest")
async def ingest(w: Window):
    s = node_state(w.node_id)
    d = w.model_dump(); ts = d.pop("ts") or time.time(); d.pop("node_id")
    if s["base"] is None:
        s["base_rows"].append(d)
        if len(s["base_rows"]) >= BASELINE_WINDOWS:
            s["base"] = F.baseline_from(s["base_rows"]); s["status"] = "monitoring"
        out = dict(node_id=w.node_id, ts=ts, status="learning", progress=len(s["base_rows"]) / BASELINE_WINDOWS, health=100, label="learning baseline")
        await broadcast(out); return out
    x = F.normalise(d, s["base"])[None, :]
    p = BOOSTER.predict(xgb.DMatrix(x, feature_names=META["features"]))[0]
    pf = float(1 - p[0]); label = CLASSES[int(np.argmax(p))]
    s["votes"].append(label != "healthy")
    s["hist"].append((ts, pf))
    alarm = len(s["votes"]) == VOTES and all(s["votes"])
    ttf = ttf_seconds(s["hist"])
    out = dict(node_id=w.node_id, ts=ts, status="alarm" if alarm else "ok", label=label, health=round(100 * (1 - pf)), p_fault=round(pf, 3), ttf_s=ttf,
               probs={c: round(float(v), 3) for c, v in zip(CLASSES, p)}, vib_rms=d["rms"], cur_rms=d["cur_rms"], temp=d["temp"])
    if alarm and not s["alerted"]:
        s["alerted"] = True
        notify(f"MotorGuard {w.node_id}: {label} suspected. Health {out['health']}/100." + (f" About {int(ttf/60)} min to failure." if ttf else ""))
    if not alarm and label == "healthy":
        s["alerted"] = False
    await broadcast(out); return out


@app.post("/reset/{nid}")
async def reset(nid: str):
    nodes.pop(nid, None); return {"ok": True}


@app.get("/state")
async def state():
    return {k: dict(status=v["status"], last=(v["hist"][-1] if v["hist"] else None)) for k, v in nodes.items()}


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept(); clients.add(sock)
    try:
        while True:
            await sock.receive_text()
    except WebSocketDisconnect:
        clients.discard(sock)


@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
