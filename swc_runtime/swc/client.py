"""
TrueLoop Compute client — a thin HTTP shim.

This module carries NO update law. Each round it posts a measured statistic and a
score to the TrueLoop endpoint and receives the next configuration to apply. The
optimization mechanism runs server-side and is never downloaded.
"""
import json
import math
import time
import urllib.request
import urllib.error

DEFAULT_ENDPOINT = "https://compute.neophotonics.ca"
__all__ = [
    "SWCOptimizer", "Regime", "swc_regulate",
    "SWCError", "SWCAuthError", "SWCLicenseExpired",
    "SWCSessionError", "SWCServerError", "SWCNetworkError", "OutOfEnvelope",
]


class SWCError(Exception): pass
class SWCAuthError(SWCError): pass
class SWCLicenseExpired(SWCError): pass
class SWCSessionError(SWCError): pass
class SWCServerError(SWCError): pass
class SWCNetworkError(SWCError): pass
class OutOfEnvelope(SWCError): pass


class Regime:
    """Describes your problem so the runtime can tell you USE / MARGINAL / DECLINE."""
    def __init__(self, baseline="optimizer", per_round_evals=1, total_budget=None,
                 n_params=None, drifting=False, related_stream=False,
                 coupled_plant=False, have_calibration=True):
        self.baseline = baseline
        self.per_round_evals = per_round_evals
        self.total_budget = total_budget
        self.n_params = n_params
        self.drifting = drifting
        self.related_stream = related_stream
        self.coupled_plant = coupled_plant
        self.have_calibration = have_calibration

    def as_dict(self):
        return self.__dict__.copy()


def _post(endpoint, path, payload, retries=3, timeout=30):
    url = endpoint.rstrip("/") + path
    data = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            code = e.code
            try:
                body = json.loads(e.read().decode("utf-8"))
            except Exception:
                body = {}
            msg = body.get("error", e.reason)
            if code == 401:
                raise SWCAuthError(msg)
            if code == 402:
                raise SWCLicenseExpired(msg)
            if code == 409:
                raise SWCSessionError(msg)
            if 500 <= code < 600:
                last = SWCServerError(msg)
                time.sleep(0.4 * (attempt + 1))
                continue
            raise SWCError("%s: %s" % (code, msg))
        except (urllib.error.URLError, TimeoutError) as e:
            last = SWCNetworkError(str(e))
            time.sleep(0.4 * (attempt + 1))
    raise last if last else SWCNetworkError("request failed")


class SWCOptimizer:
    """
    Measurement-efficient optimization runtime client.

        opt = SWCOptimizer(license_key="EVAL-...", n=len(x0))
        x = opt.start(x0)
        for _ in range(rounds):
            p_hat = measure(x)
            x = opt.step(p_hat, score=objective(x))
        opt.end()
    """
    def __init__(self, license_key, n, mode="optimization", target=None,
                 jacobian=None, config=None, endpoint=DEFAULT_ENDPOINT):
        if not license_key:
            raise SWCAuthError("license_key is required")
        self.key = license_key
        self.n = int(n)
        self.mode = mode
        self.target = list(target) if target is not None else None
        self.jacobian = jacobian
        self.config = dict(config) if config else None
        self.endpoint = endpoint
        self.session = None
        self._started = False
        self.link_signs = None

    def calibrate(self, measure, x0, eps=0.10, probe_shots=None, conf_thresh=0.12):
        """One-time link-sign calibration for OPTIMIZATION mode. Probe each control +/- eps and
        record which way the measured statistic actually moves, so the runtime steps the right
        direction even when your plant's control->observable map differs in sign from the
        default contract.

        Note: in REGULATION mode this is unnecessary. The regulation runtime learns each
        channel's drive direction (and magnitude) directly from your measurements during its
        opening probe rounds, so it already handles sign-flipped, mixed-sign, and heterogeneous
        plants on its own. To avoid fighting that auto-calibration, calibrate() does NOT apply
        sign overrides in regulation mode -- it returns the detected signs for your information
        only. In optimization mode the detected signs are applied.

        `measure(x)` must return the n-vector decoded statistic at configuration x. Use the
        cleanest measurement you can afford here (more shots = more reliable sign); this runs
        once, not per round. Call before start(). Returns the per-channel sign vector.

        Channels whose response is too flat to read confidently are left at the default (+1).
        """
        x0 = list(map(float, x0))
        base = [float(v) for v in measure(x0)]
        signs = [1.0] * self.n
        for i in range(self.n):
            xp = list(x0); xp[i] += eps
            xm = list(x0); xm[i] -= eps
            pp = [float(v) for v in measure(xp)]
            pm = [float(v) for v in measure(xm)]
            slope = (pp[i] - pm[i]) / (2.0 * eps)
            assumed = 1.0  # default expected slope sign; the runtime measures the true sign on the endpoint
            if abs(slope) > conf_thresh and ((slope > 0) != (assumed > 0)):
                signs[i] = -1.0
        # Regulation auto-learns drive direction from measurements; applying sign overrides on
        # top double-corrects and can break an otherwise-converging loop. Only apply in
        # optimization mode, where there is no per-channel sensitivity probe.
        if self.mode != "regulation":
            self.link_signs = signs
        return signs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        try:
            self.end()
        except SWCError:
            pass

    def start(self, x0):
        x0 = list(map(float, x0))
        payload = {"license_key": self.key, "n": self.n, "mode": self.mode,
                   "x0": x0}
        if self.config is not None:
            payload["config"] = self.config
        if self.target is not None:
            payload["target"] = self.target
        if self.jacobian is not None:
            payload["jacobian"] = [list(map(float, row)) for row in self.jacobian]
        if self.link_signs is not None:
            payload["link_signs"] = list(self.link_signs)
        out = _post(self.endpoint, "/api/session/start", payload)
        self.session = out["session"]
        self._started = True
        return out["config"]

    def step(self, measurement, score=None, target=None):
        if not self._started:
            raise SWCSessionError("call start(x0) before step(...)")
        payload = {"license_key": self.key, "session": self.session,
                   "measurement": list(map(float, measurement))}
        if score is not None:
            payload["score"] = float(score)
        if target is not None:
            payload["target"] = list(map(float, target))
        out = _post(self.endpoint, "/api/session/step", payload)
        return out["config"]

    def check_envelope(self, regime, require_in_envelope=False):
        payload = {"license_key": self.key, "regime": regime.as_dict()}
        out = _post(self.endpoint, "/api/envelope", payload)
        verdict = out.get("verdict", "UNKNOWN")
        if require_in_envelope and verdict == "DECLINE":
            raise OutOfEnvelope(out.get("reason", "current method already wins here"))
        return verdict

    def end(self):
        if self._started and self.session:
            try:
                _post(self.endpoint, "/api/session/end",
                      {"license_key": self.key, "session": self.session})
            finally:
                self._started = False
                self.session = None


def swc_regulate(measure, x0, target, license_key, rounds=120,
                 endpoint=DEFAULT_ENDPOINT):
    """Convenience driver for regulation/tracking: drive a measured output to `target`."""
    opt = SWCOptimizer(license_key, n=len(x0), mode="regulation",
                       target=target, endpoint=endpoint)
    x = opt.start(x0)
    history = []
    try:
        for _ in range(rounds):
            p_hat = measure(x)
            x = opt.step(p_hat, target=target)
            history.append(x)
    finally:
        opt.end()
    return x, history
