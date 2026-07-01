"""
swc_backend.py -- run the regulation benchmarks on EITHER backend.

The original benchmark.py talks to the hosted endpoint (via the bundled `swc` client),
which supports channel counts up to N=4096. To reproduce the large-N results (up to
N=100,000) you need the licensed offline build, which runs the same runtime in-process
with no cap. This shim exposes one small interface both backends satisfy, so the scale
and plant-variation scripts run unchanged against either.

  backend="endpoint"  -> hosted API via the bundled `swc` client   (N <= 4096, needs a key)
  backend="offline"   -> the licensed compiled `trueloop` package   (any N, no key)

The runtime's update law is NOT in this file. On the endpoint it runs server-side; in the
offline build it runs inside the licensed compiled package. This shim only opens a session,
sends a measurement, and reads back the configuration.
"""
import os, math

ENDPOINT_MAX_N = 4096


class _Endpoint:
    def __init__(self, n, target, key, base):
        from swc import SWCOptimizer
        self.opt = SWCOptimizer(license_key=key, n=n, mode="regulation",
                                target=list(target), endpoint=base)
        self.phi = None

    def start(self, x0):
        self.phi = self.opt.start(list(x0)); return self.phi

    def step(self, measurement, target):
        self.phi = self.opt.step(list(measurement), target=list(target)); return self.phi

    def end(self):
        try: self.opt.end()
        except Exception: pass


class _Offline:
    def __init__(self, n, target):
        try:
            import trueloop
        except Exception as e:
            raise RuntimeError(
                "backend='offline' selected but the 'trueloop' package is not importable. "
                "Unzip your licensed offline build and add its folder to PYTHONPATH "
                "(see README). Underlying error: %r" % (e,))
        self.opt = trueloop.SWCRuntime(n=n, mode="regulation", target=list(target))
        self.phi = None

    def start(self, x0):
        self.phi = self.opt.start(list(x0)); return self.phi

    def step(self, measurement, target):
        self.phi = self.opt.step(list(measurement), target=list(target)); return self.phi

    def end(self):
        try: self.opt.end()
        except Exception: pass


def open_regulation(n, target, backend=None, key=None, base=None):
    """Open a regulation session on the chosen backend. Returns an object with
    .start(x0) -> config, .step(measurement, target) -> config, and .end()."""
    backend = (backend or os.environ.get("TRUELOOP_BACKEND", "endpoint")).lower()
    if backend == "offline":
        return _Offline(n, target)
    if backend == "endpoint":
        if n > ENDPOINT_MAX_N:
            raise RuntimeError(
                "N=%d exceeds the hosted endpoint cap of %d. Use the offline build "
                "(backend='offline') for large-N runs." % (n, ENDPOINT_MAX_N))
        key = key or os.environ.get("TRUELOOP_KEY")
        if not key:
            raise RuntimeError("No key. Set TRUELOOP_KEY (endpoint backend).")
        base = base or os.environ.get("TRUELOOP_ENDPOINT", "https://compute.neophotonics.ca")
        return _Endpoint(n, target, key, base)
    raise RuntimeError("Unknown backend %r (use 'endpoint' or 'offline')." % backend)


def backend_name(backend=None):
    return (backend or os.environ.get("TRUELOOP_BACKEND", "endpoint")).lower()
