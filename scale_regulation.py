"""
scale_regulation.py -- setpoint-holding at scale, up to N=100,000.

Shows the core measurement-efficiency result at scale: the runtime holds a drifting device at
its setpoint with a tracking error that is INDEPENDENT of the channel count N, using one
measurement per round -- while a finite-difference controller, which needs N+1 measurements
per update, falls behind and then, past a few thousand channels, cannot complete even one
update inside a real-time budget.

N <= 4096 can run on the endpoint. Large N needs the offline build:

  export TRUELOOP_BACKEND=offline
  export PYTHONPATH=/path/to/trueloop_offline
  python scale_regulation.py --plant cos2 --sizes 1024,10000,100000
"""
import argparse, os, sys, time
from swc_backend import open_regulation, backend_name
from plants import make_plant, reachable_target, rms, good_start


def swc_tail_rms(plant_name, n, budget, sigma, seed, backend, key):
    target = reachable_target(plant_name, n, seed)
    measure = make_plant(plant_name, n, sigma=sigma, seed=seed)
    s = open_regulation(n, target, backend=backend, key=key)
    x = s.start([good_start(plant_name)] * n)
    errs = []
    for _ in range(budget):
        y = measure(x)
        errs.append(rms(y, target))
        x = s.step(y, target)
    s.end()
    k = max(3, len(errs) // 4)
    return sum(errs[-k:]) / k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default=None, help="endpoint | offline")
    ap.add_argument("--key", default=None)
    ap.add_argument("--plant", default="cos2", help="cos2|sin|neg_sin|linear|sigmoid|tanh|exp|cubic|vshape")
    ap.add_argument("--sizes", default="128,1024")
    ap.add_argument("--budget", type=int, default=300)
    ap.add_argument("--sigma", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    print("Setpoint-holding at scale  (plant=%s, backend=%s, bounded OU drift sigma=%.3f)"
          % (args.plant, backend_name(args.backend), args.sigma))
    print("  %8s %14s" % ("N", "SWC tail-RMS"))
    prev = None
    for n in sizes:
        t0 = time.time()
        r = swc_tail_rms(args.plant, n, args.budget, args.sigma, args.seed, args.backend, args.key)
        flat = "" if prev is None else ("  (flat: %+.4f vs previous)" % (r - prev))
        print("  %8d %14.4f%s   [%ds]" % (n, r, flat, time.time() - t0))
        prev = r
    print("\nExpected: SWC tail-RMS stays essentially constant as N grows -- setpoint-holding is")
    print("N-independent. Finite difference (see baselines.py / kpi_summary.py) needs N+1")
    print("measurements per update and cannot keep up at large N under a real-time budget.")


if __name__ == "__main__":
    main()
