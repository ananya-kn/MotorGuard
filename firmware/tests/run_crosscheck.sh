#!/bin/sh
# Compiles features.h on the host and compares against ml/features.py on 5 synthetic windows.
set -e
cd "$(dirname "$0")"
g++ -O2 -std=c++17 -o /tmp/mg_feat test_features.cpp
python3 - <<'PY'
import sys, subprocess, numpy as np
sys.path.insert(0, "../../ml")
import sim
from features import vib_features, NAMES
rng = np.random.default_rng(7)
worst = 0
for i, fault in enumerate(["healthy", "imbalance", "misalignment", "looseness", "bearing"]):
    m = sim.new_machine(rng)
    ax, ay, az, _, _ = sim.window(m, fault, 0.7, rng)
    np.savetxt("/tmp/win.csv", np.c_[ax, ay, az], delimiter=",", fmt="%.6f")
    ref = vib_features(*np.loadtxt("/tmp/win.csv", delimiter=",", unpack=True))
    out = [float(x) for x in subprocess.check_output(["/tmp/mg_feat", "/tmp/win.csv"]).split()]
    for n, c in zip(NAMES, out):
        rel = abs(c - ref[n]) / (abs(ref[n]) + 1e-6)
        worst = max(worst, rel)
        if rel > 2e-3:
            print("MISMATCH", fault, n, ref[n], c)
print("worst relative difference: %.2e" % worst)
sys.exit(0 if worst < 2e-3 else 1)
PY
