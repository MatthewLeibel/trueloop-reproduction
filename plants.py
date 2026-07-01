"""
plants.py -- a family of physically distinct simulated devices, with realistic bounded drift.

The core `plant.py` in this bundle is the ONE file you edit to attach real hardware. This
module is different: it provides several *simulated* device responses so you can verify that
setpoint-holding is a property of the runtime, not of any one response shape. Each plant maps
a control vector to a measured output in [0,1]^N, with per-channel Ornstein-Uhlenbeck drift
(mean-reverting and bounded -- how real hardware wanders around an operating point, rather
than a random walk to infinity).

numpy is used here only to make the large-N (up to 100,000) simulations fast. The runtime
itself never sees numpy; it receives plain lists.
"""
import math

try:
    import numpy as np
    _HAVE_NP = True
except Exception:
    _HAVE_NP = False


# Each response takes (phi, off) arrays and returns measured output in [0,1].
def _cos2(phi, off):    return np.clip(0.5 * (1 + np.cos(phi + off)), 0, 1)
def _sin(phi, off):     return np.clip(0.5 * (1 + np.sin(phi + off)), 0, 1)
def _neg_sin(phi, off): return -0.5 * np.sin(phi + off)                       # signed, meas-space
def _linear(phi, off):  return np.clip(0.15 * (phi + off) + 0.1, 0, 1)
def _sigmoid(phi, off): return np.clip(1 / (1 + np.exp(-(1.2 * (phi + off) - 3.0))), 0, 1)
def _tanh(phi, off):    return np.clip(0.5 * (1 + np.tanh(0.8 * (phi + off) - 1.5)), 0, 1)
def _exp(phi, off):     return np.clip(1 - np.exp(-0.6 * np.abs(phi + off)), 0, 1)
def _cubic(phi, off):
    x = (phi + off - 1.5) / 2.0
    return np.clip(0.5 + 0.5 * np.sign(x) * np.abs(x) ** 1.5, 0, 1)
def _vshape(phi, off):  return np.clip(np.abs(phi + off - 1.5) / 2.5, 0, 1)
def _quad(phi, off):    return np.clip(((phi + off - 1.5) / 2.0) ** 2, 0, 1)   # NON-monotone

RESPONSES = {
    "cos2": _cos2, "sin": _sin, "neg_sin": _neg_sin, "linear": _linear,
    "sigmoid": _sigmoid, "tanh": _tanh, "exp": _exp, "cubic": _cubic,
    "vshape": _vshape, "quad": _quad,
}

# Which plants are monotone (or piecewise-monotone) over the working range -- the runtime is
# expected to hold these. `quad` is non-monotone and only regulates from a start on a slope.
MONOTONE = {"cos2", "sin", "neg_sin", "linear", "sigmoid", "tanh", "exp", "cubic", "vshape"}


def make_plant(name, n, sigma=0.03, seed=1, theta=0.05):
    """Return a `measure(phi)->list` closure for the named response with bounded OU drift.
    Requires numpy for large N (installed only for these scale demos)."""
    if not _HAVE_NP:
        raise RuntimeError("plants.py needs numpy for the scale demos: pip install numpy")
    fn = RESPONSES[name]
    rng = np.random.default_rng(seed)
    state = {"off": np.zeros(n)}

    def measure(phi):
        state["off"] = state["off"] * (1 - theta) + rng.normal(0, sigma, n)
        return fn(np.asarray(phi, dtype=float), state["off"]).tolist()

    return measure


def reachable_target(name, n, seed=1):
    """A per-channel target vector that the named plant can actually reach, in measurement space."""
    import random
    rng = random.Random(seed * 7 + 3)
    if name in ("cos2", "sin", "linear", "sigmoid", "tanh", "exp", "cubic", "vshape"):
        return [0.3 + 0.4 * ((i % 5) / 4.0) for i in range(n)]
    if name == "neg_sin":
        ang = [rng.uniform(-1.4, 1.4) for _ in range(n)]
        return [-0.5 * math.sin(a) for a in ang]
    if name == "quad":
        return [0.5] * n
    return [0.5] * n


def good_start(name):
    """A sensible starting control value for each plant (off any flat extremum). The runtime
    is model-free, but like any feedback controller it needs to begin somewhere on a slope."""
    return {"quad": 0.3}.get(name, 0.0)


def rms(y, target):
    n = len(y)
    return math.sqrt(sum((y[i] - target[i]) ** 2 for i in range(n)) / n)
