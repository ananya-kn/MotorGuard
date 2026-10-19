"""Fake node for demos without hardware: learns baseline, runs healthy, then ramps an imbalance fault.
  python sim_node.py --url http://localhost:8000 --fault imbalance --interval 0.3"""
import argparse, sys, os, time
import numpy as np, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ml"))
import sim

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://localhost:8000"); ap.add_argument("--node", default="Pump-03")
ap.add_argument("--fault", default="imbalance", choices=sim.CLASSES[1:]); ap.add_argument("--interval", type=float, default=0.3)
ap.add_argument("--baseline", type=int, default=30); ap.add_argument("--healthy", type=int, default=20); ap.add_argument("--ramp", type=int, default=40)
a = ap.parse_args()
rng = np.random.default_rng(); m = sim.new_machine(rng)
plan = [("healthy", 0.0)] * (a.baseline + a.healthy) + [(a.fault, 0.05 + 0.95 * i / a.ramp) for i in range(a.ramp)]
for i, (f, s) in enumerate(plan):
    d = sim.features(m, f, s, rng); d["node_id"] = a.node
    r = requests.post(a.url + "/ingest", json=d, timeout=5).json()
    print(i, f, round(s, 2), r.get("status"), r.get("label"), r.get("health"))
    time.sleep(a.interval)
