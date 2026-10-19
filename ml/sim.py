"""Physics-inspired synthetic vibration/current/temperature generator for MotorGuard.
It exists so the pipeline, dashboard and demo work BEFORE the hardware does. Real rig data
(ml/real_data.py) should replace or fine-tune it; synthetic accuracy is NOT a field claim."""
import numpy as np
from features import N, FS, vib_features

CLASSES = ["healthy", "imbalance", "misalignment", "looseness", "bearing", "overload"]


def lp(x, bw=260.0):
    """2nd-order Butterworth magnitude response (zero phase) modelling the MPU6050 accelerometer bandwidth."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    return np.fft.irfft(X / np.sqrt(1 + (f / bw) ** 4), len(x))


def new_machine(rng):
    f0 = rng.uniform(20, 50)
    th = rng.uniform(0, np.pi)
    return dict(
        f0=f0, a1=rng.uniform(0.01, 0.05), noise=rng.uniform(0.008, 0.03),
        radial=np.array([np.cos(th), np.sin(th), 0.0]), f_res=rng.uniform(320, 450),
        I0=rng.uniform(0.8, 3.0), T0=rng.uniform(30, 45), gain=rng.uniform(0.7, 1.4))


def window(m, fault="healthy", sev=0.0, rng=None):
    rng = rng or np.random.default_rng()
    t = np.arange(N) / FS
    f0 = m["f0"] * (1 + rng.normal(0, 0.002))
    a1, a2, a3 = m["a1"], 0.15 * m["a1"], 0.05 * m["a1"]
    axial, imp = 0.1 * m["a1"], 0.0
    I, T = m["I0"], m["T0"]
    if fault == "imbalance":
        a1 *= 1 + (0.15 + 12 * sev)
    elif fault == "misalignment":
        a1 *= 1 + 1.5 * sev
        a2 += m["a1"] * (0.2 + 12 * sev)
        axial += m["a1"] * (0.2 + 8 * sev)
    elif fault == "overload":
        I *= 1 + 0.02 + 0.5 * sev
        T += 0.5 + 12 * sev
        a1 *= 1 + 0.6 * sev
    ph = rng.uniform(0, 2 * np.pi, 12)
    s = a1 * np.sin(2 * np.pi * f0 * t + ph[0]) + a2 * np.sin(4 * np.pi * f0 * t + ph[1]) + a3 * np.sin(6 * np.pi * f0 * t + ph[2])
    sa = axial * np.sin(2 * np.pi * f0 * t + ph[3]) + 0.6 * axial * np.sin(4 * np.pi * f0 * t + ph[4])
    if fault == "looseness":
        amp = m["a1"] * (1 + 4 * sev)
        s += 0.5 * amp * np.sin(np.pi * f0 * t + ph[5])
        for k in range(2, 11):
            s += (amp * (0.1 + 2.5 * sev) / k ** 0.7) * np.sin(2 * np.pi * k * f0 * t + ph[k % 12])
        s += np.where(rng.random(N) < 0.01, rng.normal(0, 0.1 * (0.5 + sev), N), 0)
    if fault == "bearing":
        fb = 3.58 * f0 * (1 + rng.normal(0, 0.01))
        pos, tau = np.arange(0, N / FS, 1.0 / fb), 0.004
        burst = np.zeros(N)
        for p in pos:
            p += rng.normal(0, 0.0003)
            idx = np.arange(max(int(p * FS), 0), min(int(p * FS) + 25, N))
            if len(idx):
                tt = idx / FS - p
                burst[idx] += np.exp(-tt / tau) * np.sin(2 * np.pi * m["f_res"] * tt)
        s += (0.004 + 0.25 * sev) * burst * rng.uniform(0.7, 1.3)
        a1 *= 1.0
    s, sa = lp(s), lp(sa)  # MPU6050 accel bandwidth is ~260 Hz with DLPF off (see docs/known_limits.md)
    mix = m["radial"] * s[:, None]
    ax_ = (mix[:, 0] + 0.2 * np.roll(s, 3)) * m["gain"] + rng.normal(0, m["noise"], N)
    ay_ = (mix[:, 1]) * m["gain"] + rng.normal(0, m["noise"], N)
    az_ = sa * m["gain"] + rng.normal(0, m["noise"], N) + 1.0  # gravity on z
    cur = I * (1 + rng.normal(0, 0.01)) + rng.normal(0, 0.01 * I)
    return ax_, ay_, az_, float(cur), float(T + rng.normal(0, 0.15))


def features(m, fault="healthy", sev=0.0, rng=None):
    ax, ay, az, cur, tmp = window(m, fault, sev, rng)
    d = vib_features(ax, ay, az)
    d["cur_rms"], d["temp"] = cur, tmp
    return d
