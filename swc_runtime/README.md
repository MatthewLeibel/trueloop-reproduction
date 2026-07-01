# swc-runtime — TrueLoop Compute client

The measurement-efficient optimization runtime. This package is a thin, standard-library
HTTP client: each round you send a measured statistic and a score, and receive the next
configuration. The update law runs on TrueLoop's endpoint — it is never downloaded, so
there is nothing to leak in either direction.

## Install
Install from this bundle (no PyPI account or internet index needed):

    pip install ./swc_runtime        # run from the folder this README is in

Or skip pip entirely — just drop the swc/ folder next to your code and import it.
## Quickstart
    from swc import SWCOptimizer
    opt = SWCOptimizer(license_key="EVAL-...", n=len(x0))
    x = opt.start(x0)
    for _ in range(rounds):
        p_hat = measure(x)
        x = opt.step(p_hat, score=objective(x))
    opt.end()

Full docs: https://trueloopcompute.com/docs
