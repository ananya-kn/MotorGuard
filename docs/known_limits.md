# Known limits (read before you present)

1. **MPU6050 bandwidth.** With the DLPF off the accelerometer bandwidth is about 260 Hz. Bearing-defect resonances often sit at 300-450 Hz, so bearing detection is weaker than imbalance/misalignment. The simulator models this (see `ml/sim.py: lp()`), and the held-out bearing recall is the lowest class. Upgrade path: ADXL345 (SPI, 1.6 kHz bandwidth) or ADXL355. Say "10-260 Hz" or "up to the sensor bandwidth", not "10-500 Hz", unless you change the sensor.
2. **SCT-013 measures AC only.** The 12 V DC test rig needs the INA219 (default in `config.h`). SCT-013 + ADS1115 is the AC-motor path; test it on a supervised mains motor (isolated, RCD) or skip it for the demo.
3. **Synthetic results are a pipeline check, not a field claim.** `docs/results/metrics.json` holds out whole synthetic machines. Real accuracy comes from `tools/collect_serial.py` data and `python ml/train.py --real data/`.
4. **Edge anomaly is a z-score on rms/high-band energy** (plus a hard rms limit). The deck's "TinyML autoencoder" wording should say "on-device anomaly score" unless you implement and flash a small autoencoder.
5. **Firmware is untested on hardware.** The feature code is cross-checked against Python on the host; the sensor/network code is syntax-checked only. Bring up sensor by sensor (serial prints first).
6. **Time-to-failure** is a linear extrapolation of the fault probability. It is an indicator, not a calibrated remaining-life model.
