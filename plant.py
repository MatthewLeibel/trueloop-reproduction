"""
plant.py  --  THE ONE FILE YOU EDIT.

To run the benchmark on your own hardware, replace the body of `measure()` and
`apply()` below so they talk to your device. Everything else in this bundle is
hardware-agnostic and does not need to change.

THE CONTRACT (this is all the runtime needs):
  - A writable control configuration: an N-vector `x` you can apply to the device.
  - A measurable output: an N-vector `y` in [0, 1]^N read back from the device.
  - Each channel's output should move consistently (locally monotonic) when you
    move its control over your operating range. Sign, gain, and shape are learned
    from measurement -- you do NOT need to calibrate or model the device.

A simulated plant is provided so the bundle runs out-of-the-box with no hardware.
Swap it for your device by editing the two marked functions.
"""
import math
import random

# ============================================================================ #
#  SIMULATED PLANT (default).  DELETE or ignore once you wire up real hardware. #
# ============================================================================ #

class SimulatedPlant:
    """A drifting, nonlinear, multi-channel parametric plant.

    Stands in for a real device (e.g. a photonic mesh under thermal drift) so the
    benchmark runs with no hardware. Per channel: y_i = sin(x_i * pi/2 * g_i),
    clamped to [0,1], with per-channel gains and slow drift.
    """
    def __init__(self, n, seed=1, drift_rate=0.15):
        rng = random.Random(seed)
        self.n = n
        self.gains = [rng.uniform(0.6, 1.4) for _ in range(n)]
        self.phase = [rng.uniform(0, 2 * math.pi) for _ in range(n)]
        self.drift_rate = drift_rate
        self._t = 0

    def read(self, x):
        t = self._t
        self._t += 1
        g = self.gains
        if self.drift_rate > 0:
            g = [self.gains[i] * (1.0 + self.drift_rate * math.sin(0.05 * t + self.phase[i]))
                 for i in range(self.n)]
        return [min(1.0, max(0.0, math.sin(x[i] * math.pi / 2 * g[i]))) for i in range(self.n)]


# A single module-level instance the functions below read from. For real
# hardware you will not need this object at all.
_SIM = None


def make_plant(n, seed=1, drift_rate=0.15):
    """Construct (or reconstruct) the default simulated plant. For real hardware,
    you can leave this returning None and ignore it."""
    global _SIM
    _SIM = SimulatedPlant(n, seed=seed, drift_rate=drift_rate)
    return _SIM


# ============================================================================ #
#  >>> EDIT THESE TWO FUNCTIONS TO USE YOUR HARDWARE <<<                        #
# ============================================================================ #

def apply(x):
    """Write the control configuration `x` (an N-vector) to your device.

    SIMULATED default: the simulated plant reads `x` directly in `measure()`, so
    there is nothing to apply separately. For REAL HARDWARE, send `x` to your
    device here (e.g. set phase-shifter voltages, DAC channels, actuator setpoints).
    Return nothing.
    """
    # --- REAL HARDWARE: replace this body, e.g. ---
    # device.set_phase_voltages(x)        # your driver call
    # time.sleep(settle_seconds)          # let the device settle if needed
    pass


def measure(x):
    """Apply `x`, then read and return the device output as an N-vector in [0,1]^N.

    This is the function the benchmark calls every round. The runtime sends a
    measurement and a score and returns the next configuration; this function is
    where your physical measurement happens.

    SIMULATED default: returns the simulated plant's response.
    For REAL HARDWARE: apply x, read your detector(s), normalise to [0,1], return.
    """
    # --- REAL HARDWARE: replace this body, e.g. ---
    # apply(x)
    # raw = device.read_detectors()       # your driver call -> length-N
    # return [normalise(v) for v in raw]  # map each reading into [0,1]
    if _SIM is None:
        raise RuntimeError("Call make_plant(n) first, or wire up real hardware in measure().")
    return _SIM.read(x)


# ============================================================================ #
#  Helpers (hardware-agnostic; no need to edit)                                #
# ============================================================================ #

def default_target(n):
    """A reachable, non-trivial setpoint vector in [0,1]^N used by the benchmark."""
    return [0.3 + 0.4 * ((i % 5) / 4.0) for i in range(n)]


def tracking_rms(y, target):
    n = len(y)
    return math.sqrt(sum((y[i] - target[i]) ** 2 for i in range(n)) / n)
