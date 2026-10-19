"""MotorGuard feature extraction. MUST stay identical to firmware/motorguard_node/mg_features.h.
Window: N=1024 samples at 1 kHz, three axes in g. Cross-checked against the C++ in firmware/tests."""
import numpy as np

N = 1024
FS = 1000.0
DF = FS / N
NAMES = ["rms", "crest", "kurt", "f_run", "a1x", "a2x", "a3x", "r21", "e_low", "e_mid", "e_high", "centroid"]


def kbin(f):
    return int(f * N / FS + 0.5)


def vib_features(ax, ay, az):
    """ax, ay, az: arrays of length N (g). Returns dict of 12 vibration features."""
    axes = [np.asarray(a, dtype=np.float64) - np.mean(a) for a in (ax, ay, az)]
    r2 = axes[0] ** 2 + axes[1] ** 2 + axes[2] ** 2
    rms = np.sqrt(np.mean(r2))
    crest = np.sqrt(r2.max()) / (rms + 1e-12)
    kurt = 0.0
    for a in axes:
        v = np.mean(a ** 2)
        kurt += np.mean(a ** 4) / (v * v + 1e-24)
    kurt /= 3.0
    w = 0.5 * (1.0 - np.cos(2 * np.pi * np.arange(N) / (N - 1)))
    P = np.zeros(N // 2)
    for a in axes:
        X = np.fft.rfft(a * w)[: N // 2]
        P += np.abs(X) ** 2
    A = 4.0 * np.sqrt(P) / N
    A[0] = 0.0
    lo, hi = kbin(10), kbin(100)
    k = lo + int(np.argmax(A[lo:hi + 1]))
    f_run = k * DF

    def amp(kk):
        if kk + 1 >= N // 2:
            return 0.0
        return float(A[kk - 1:kk + 2].max())

    a1, a2, a3 = amp(k), amp(2 * k), amp(3 * k)
    e_low = float(np.sum(A[kbin(10):kbin(100)] ** 2))
    e_mid = float(np.sum(A[kbin(100):kbin(250)] ** 2))
    e_high = float(np.sum(A[kbin(250):N // 2] ** 2))
    ks = np.arange(kbin(10), N // 2)
    centroid = float(np.sum(ks * DF * A[ks]) / (np.sum(A[ks]) + 1e-12))
    return dict(rms=rms, crest=crest, kurt=kurt, f_run=f_run, a1x=a1, a2x=a2, a3x=a3,
                r21=a2 / (a1 + 1e-9), e_low=e_low, e_mid=e_mid, e_high=e_high, centroid=centroid)


# Features that scale with machine size/mounting: normalised by the machine's own healthy baseline
RATIO = ["rms", "a1x", "a2x", "a3x", "e_low", "e_mid", "e_high", "cur_rms"]
RAW = ["crest", "kurt", "r21", "centroid"]
MODEL_FEATURES = [f + "_rel" for f in RATIO] + RAW + ["temp_rise"]


def baseline_from(feature_dicts):
    keys = RATIO + ["temp"]
    return {k: float(np.mean([d[k] for d in feature_dicts])) for k in keys}


def normalise(d, base):
    v = [d[k] / (base[k] + 1e-9) for k in RATIO] + [d[k] for k in RAW] + [d["temp"] - base["temp"]]
    return np.array(v, dtype=np.float64)
