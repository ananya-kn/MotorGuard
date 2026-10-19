"""Train + honestly evaluate the MotorGuard classifier.
  python train.py                 -> synthetic machines (pipeline check)
  python train.py --real data/    -> add real rig windows (machine-wise split, no leakage)
Evaluation always holds out WHOLE MACHINES, never random windows of a machine seen in training."""
import argparse, json, os
import numpy as np
import xgboost as xgb
from sklearn.metrics import confusion_matrix, roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sim, features as F

ap = argparse.ArgumentParser()
ap.add_argument("--machines", type=int, default=80)
ap.add_argument("--real", default=None)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
rng = np.random.default_rng(a.seed)
C = sim.CLASSES


def build(machine_rows):
    X, y, g, sev = [], [], [], []
    for mid, rows in machine_rows.items():
        base = F.baseline_from([d for lab, s, d in rows if lab == "healthy"][:30])
        for lab, s, d in rows:
            X.append(F.normalise(d, base)); y.append(C.index(lab)); g.append(mid); sev.append(s)
    return np.array(X), np.array(y), np.array(g), np.array(sev)


data = {}
for i in range(a.machines):
    m = sim.new_machine(rng)
    rows = [("healthy", 0.0, sim.features(m, "healthy", 0, rng)) for _ in range(60)]
    for fault in C[1:]:
        for _ in range(25):
            s = rng.uniform(0.02, 1.0)
            rows.append((fault, s, sim.features(m, fault, s, rng)))
    data[f"sim{i}"] = rows
if a.real:
    import real_data
    for mach, lab, d in real_data.load(a.real):
        data.setdefault(mach, []).append((lab, 1.0, d))
X, y, g, sev = build(data)
mids = np.array(sorted(set(g)))
rng.shuffle(mids)
test_m = set(mids[: int(0.3 * len(mids))])
te = np.array([x in test_m for x in g])
params = dict(n_estimators=250, max_depth=4, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, objective="multi:softprob", eval_metric="mlogloss")
clf = xgb.XGBClassifier(**params).fit(X[~te], y[~te])
P = clf.predict_proba(X[te])
pred = P.argmax(1)
yt, st = y[te], sev[te]
cm = confusion_matrix(yt, pred, labels=range(len(C)))
healthy = yt == 0
metrics = dict(
    note="Synthetic data unless --real is used. Held-out = unseen machines.",
    n_train_windows=int((~te).sum()), n_test_windows=int(te.sum()), n_test_machines=len(test_m),
    accuracy=float((pred == yt).mean()),
    healthy_false_alarm_rate=float((pred[healthy] != 0).mean()),
    fault_detect_recall_any=float((pred[~healthy] != 0).mean()),
    per_class_recall={C[i]: float(cm[i, i] / max(cm[i].sum(), 1)) for i in range(len(C))},
    auc_healthy_vs_fault=float(roc_auc_score(~healthy, 1 - P[:, 0])),
    recall_by_severity={f"{lo:.1f}-{hi:.1f}": float((pred[(~healthy) & (st >= lo) & (st < hi)] != 0).mean()) for lo, hi in [(0.0, 0.1), (0.1, 0.2), (0.2, 0.4), (0.4, 0.7), (0.7, 1.01)]})
os.makedirs("model", exist_ok=True)
clf.get_booster().save_model("model/motorguard.json")
json.dump(dict(classes=C, features=F.MODEL_FEATURES), open("model/meta.json", "w"), indent=1)
os.makedirs("../docs/results", exist_ok=True)
json.dump(metrics, open("../docs/results/metrics.json", "w"), indent=1)
fig, ax = plt.subplots(figsize=(5.2, 4.4))
cmn = cm / cm.sum(1, keepdims=True)
ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
ax.set_xticks(range(len(C))); ax.set_xticklabels(C, rotation=40, ha="right", fontsize=8)
ax.set_yticks(range(len(C))); ax.set_yticklabels(C, fontsize=8)
for i in range(len(C)):
    for j in range(len(C)):
        ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=7, color="white" if cmn[i, j] > .5 else "black")
ax.set_title("Held-out machines (synthetic): row-normalised", fontsize=9)
fig.tight_layout(); fig.savefig("../docs/results/confusion_matrix.png", dpi=160)
print(json.dumps(metrics, indent=1))
