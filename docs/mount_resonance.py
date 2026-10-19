"""Hand calculation: first natural frequency of the cantilever sensor mount (Rayleigh effective mass).
python mount_resonance.py   -> prints the numbers used in the Stage 2 deck. Edit the geometry to match your CAD."""
import numpy as np


def f1(E, rho, b=25e-3, h=4e-3, L=30e-3, ms=2.5e-3):
    I = b * h ** 3 / 12
    k = 3 * E * I / L ** 3
    m_eff = ms + 0.236 * rho * b * h * L
    return k, np.sqrt(k / m_eff) / (2 * np.pi)


for name, E, rho in [("Al 6061", 68.9e9, 2700), ("PETG", 2.1e9, 1270)]:
    k, f = f1(E, rho)
    print(f"{name}: k = {k/1e6:.2f} MN/m, f1 = {f:,.0f} Hz, ratio to 50 Hz run speed = {f/50:.0f}x")
