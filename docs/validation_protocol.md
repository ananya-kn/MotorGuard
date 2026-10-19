# Data collection and validation protocol (MotorGuard)

Goal: replace synthetic numbers with measured ones that a judge can trust.

1. **Machines/sessions.** Use at least 3 different mounting sessions (re-clamp the sensor each time) or 2+ different motors. The split is by machine, so a single motor in a single session proves nothing.
2. **Healthy baseline.** 10 minutes of healthy running per session at 2 speeds (`--label healthy`).
3. **Faults, one at a time, 3 severities each:**
   - imbalance: M3 bolt+nut on the disc at radius 22 mm (1, 2, 3 nuts)
   - misalignment: shim one motor foot (0.5, 1, 2 mm) on the rig
   - looseness: back off one mounting bolt (1/4, 1/2, 1 turn)
   - overload: brake the shaft lightly with a rubber pad; log current
   - bearing: only if you have a spare bearing with a known defect. Do not damage a good one for the demo.
4. **Record.** `python tools/collect_serial.py --port <port> --machine rig1 --label imbalance --count 60 --out data` (RAW_DUMP=1 in config.h).
5. **Train + report.** `python ml/train.py --real data/` then copy `docs/results/metrics.json` and the confusion matrix into the deck. Report recall, false alarms and lead time on held-out sessions only.
6. **Lead time.** Ramp a fault slowly (add nuts one by one) and note how long before failure the alarm fires.
