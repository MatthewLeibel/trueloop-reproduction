"""
benchmark.py  --  measurement-efficiency reproduction, on the live TrueLoop endpoint.

WHAT THIS SHOWS
  Under drift, at an equal measurement budget, the TrueLoop runtime holds a
  multi-channel output at a setpoint far tighter than finite-difference and SPSA
  gradient methods -- and the advantage widens as the channel count grows. The
  runtime spends one measurement per update; the gradient baselines spend n+1 and
  2 respectively, so at a fixed budget they fall behind a moving target.

HOW TO RUN
  1. Get a free 90-day evaluation key at https://compute.neophotonics.ca/
  2. pip install the bundled client:   pip install ./swc_runtime
  3. export TRUELOOP_KEY=EVAL-xxxxxxxxxxxxxxxxxxxxxxxx
  4. python benchmark.py
     -> runs on the SIMULATED plant out of the box.
  5. To run on YOUR HARDWARE: edit measure()/apply() in plant.py, then re-run.

WHAT CROSSES THE WIRE
  Only a configuration vector and a scalar per round. Your raw measurements stay
  on your machine. The update law runs server-side and is never downloaded.
"""
import os
import sys
import json
import math
import statistics

import plant
import baselines
from swc import swc_regulate

ENDPOINT = os.environ.get("TRUELOOP_ENDPOINT", "https://compute.neophotonics.ca")
KEY = os.environ.get("TRUELOOP_KEY", "").strip()

# Benchmark configuration. Channel counts to sweep, drift, and the equal budget.
SIZES = [int(s) for s in os.environ.get("TRUELOOP_SIZES", "8,32,128,256").split(",")]
ROUNDS = int(os.environ.get("TRUELOOP_ROUNDS", "80"))   # = SWC measurement budget
DRIFT = float(os.environ.get("TRUELOOP_DRIFT", "0.15"))
SEEDS = [1, 2, 3]


def require_key():
    if not KEY:
        sys.exit(
            "No evaluation key found.\n"
            "  1. Get a free key at https://compute.neophotonics.ca/\n"
            "  2. export TRUELOOP_KEY=EVAL-xxxxxxxxxxxxxxxxxxxxxxxx\n"
            "  3. re-run: python benchmark.py")


def run_swc(n, seed):
    plant.make_plant(n, seed=seed, drift_rate=DRIFT)
    target = plant.default_target(n)
    x, _ = swc_regulate(plant.measure, [0.5] * n, target, KEY,
                        rounds=ROUNDS, endpoint=ENDPOINT)
    return plant.tracking_rms(plant.measure(x), target), ROUNDS


def run_finite_difference(n, seed, budget):
    plant.make_plant(n, seed=seed, drift_rate=DRIFT)
    target = plant.default_target(n)
    fd_rounds = max(1, budget // (n + 1))   # match the measurement budget
    x, yf, meas = baselines.finite_difference_regulate(
        plant.measure, [0.5] * n, target, fd_rounds)
    return plant.tracking_rms(yf, target), meas


def run_spsa(n, seed, budget):
    plant.make_plant(n, seed=seed, drift_rate=DRIFT)
    target = plant.default_target(n)
    spsa_rounds = max(1, budget // 2)       # 2 measurements/update
    x, yf, meas = baselines.spsa_regulate(
        plant.measure, [0.5] * n, target, spsa_rounds, seed=seed)
    return plant.tracking_rms(yf, target), meas


def main():
    require_key()
    print("TrueLoop measurement-efficiency reproduction")
    print(f"endpoint={ENDPOINT}  budget={ROUNDS} measurements  drift={DRIFT}\n")
    print(f"{'n':>5} {'SWC RMS':>9} {'FiniteDiff RMS':>15} {'SPSA RMS':>10} "
          f"{'SWC/FD':>8} {'meas (SWC|FD|SPSA)':>20}")
    results = {}
    for n in SIZES:
        print(f"  running n={n} ... (live calls to the endpoint, this can take ~30-90s per size)", flush=True)
        sw = [run_swc(n, s) for s in SEEDS]
        fd = [run_finite_difference(n, s, ROUNDS) for s in SEEDS]
        sp = [run_spsa(n, s, ROUNDS) for s in SEEDS]
        swc_rms = statistics.median([r for r, _ in sw])
        fd_rms = statistics.median([r for r, _ in fd])
        sp_rms = statistics.median([r for r, _ in sp])
        ratio = fd_rms / swc_rms if swc_rms > 0 else float("inf")
        meas = f"{sw[0][1]}|{fd[0][1]}|{sp[0][1]}"
        results[n] = {"swc": swc_rms, "fd": fd_rms, "spsa": sp_rms, "ratio": ratio}
        print(f"{n:>5} {swc_rms:>9.4f} {fd_rms:>15.4f} {sp_rms:>10.4f} "
              f"{ratio:>7.0f}x {meas:>20}")
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nExpected shape: SWC RMS stays low and roughly flat as n grows, while the")
    print("gradient baselines climb -- their per-update measurement cost eats the equal")
    print("budget under drift. The SWC/FD ratio is large and widens with n.")
    print("\nSaved results.json. To run on your hardware, edit plant.py and re-run.")


if __name__ == "__main__":
    main()
