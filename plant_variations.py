"""
plant_variations.py -- setpoint-holding is a property of the runtime, not of one plant.

Runs the runtime against several physically distinct device responses (periodic, linear,
saturating, non-smooth) and reports the tracking RMS for each. The point: the runtime holds
the setpoint without knowing the response shape (it is model-free), across all monotone and
piecewise-monotone plants. The one non-monotone case (`quad`) is included to show the honest
limit -- it regulates only when started off its flat extremum, which is a general property of
feedback control, not of this runtime.

  export TRUELOOP_BACKEND=offline
  export PYTHONPATH=/path/to/trueloop_offline
  python plant_variations.py --n 10000
"""
import argparse, time
from swc_backend import open_regulation, backend_name
from plants import make_plant, reachable_target, rms, good_start, RESPONSES, MONOTONE


def hold_rms(plant_name, n, budget, sigma, seed, backend, key):
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
    ap.add_argument("--backend", default=None)
    ap.add_argument("--key", default=None)
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--budget", type=int, default=400)
    ap.add_argument("--sigma", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    order = ["cos2", "sin", "neg_sin", "linear", "sigmoid", "tanh", "exp", "cubic", "vshape", "quad"]
    print("Plant variations at N=%d  (backend=%s, bounded OU drift)" % (args.n, backend_name(args.backend)))
    print("  %-9s %13s  %s" % ("plant", "tail-RMS", "verdict"))
    for name in order:
        t0 = time.time()
        r = hold_rms(name, args.n, args.budget, args.sigma, args.seed, args.backend, args.key)
        if name in MONOTONE:
            verdict = "holds" if r < 0.07 else "check"
        else:
            verdict = "holds" if r < 0.07 else "non-monotone (needs start off the flat extremum)"
        print("  %-9s %13.4f  %s   [%ds]" % (name, r, verdict, time.time() - t0))
    print("\nExpected: every monotone / piecewise-monotone plant holds (RMS at the noise floor),")
    print("model-free -- the runtime is not told the response shape. `quad` is non-monotone and")
    print("only regulates when not started exactly at its flat minimum (a general feedback limit).")


if __name__ == "__main__":
    main()
