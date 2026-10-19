"""Load REAL rig windows. File naming: <machine>_<label>_<idx>.csv, label in sim.CLASSES.
First line: '# cur_rms=1.82,temp=38.4'. Then 1024 lines: ax,ay,az (g). Produced by tools/collect_serial.py."""
import glob, os, re
import numpy as np
from features import vib_features


def load(dir_):
    rows = []
    for f in sorted(glob.glob(os.path.join(dir_, "*.csv"))):
        machine, label, _ = os.path.basename(f)[:-4].rsplit("_", 2)
        meta = dict(kv.split("=") for kv in open(f).readline().strip("# \n").split(","))
        ax, ay, az = np.loadtxt(f, delimiter=",", skiprows=1, unpack=True)
        d = vib_features(ax, ay, az)
        d["cur_rms"], d["temp"] = float(meta["cur_rms"]), float(meta["temp"])
        rows.append((machine, label, d))
    return rows
