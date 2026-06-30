"""
baselines.py  --  classical comparison controllers (hardware-agnostic).

These are the methods the runtime is benchmarked against. They call the SAME
plant.measure() you provide, so the comparison is fair: every method drives your
device, and we count the measurements each one spends.

  - finite_difference_regulate: estimates a gradient by probing each channel.
    Costs n+1 measurements per update step.
  - spsa_regulate: simultaneous-perturbation stochastic approximation.
    Costs 2 measurements per update step.

Neither is the TrueLoop update law; both are standard, fairly-implemented
classical baselines included so you can see the difference yourself.
"""
import random


def finite_difference_regulate(measure, x0, target, rounds, lr=0.30, eps=0.05):
    """Finite-difference gradient descent on tracking error. n+1 measurements/update."""
    n = len(x0)
    x = list(x0)
    meas = 0
    for _ in range(rounds):
        y0 = measure(x); meas += 1
        l0 = sum((y0[i] - target[i]) ** 2 for i in range(n))
        grad = [0.0] * n
        for i in range(n):
            xi = list(x); xi[i] += eps
            yi = measure(xi); meas += 1
            li = sum((yi[j] - target[j]) ** 2 for j in range(n))
            grad[i] = (li - l0) / eps
        x = [x[i] - lr * grad[i] for i in range(n)]
    yf = measure(x); meas += 1
    return x, yf, meas


def spsa_regulate(measure, x0, target, rounds, a=0.20, c=0.10, seed=0):
    """SPSA tracking. 2 measurements/update (the perturbation pair)."""
    rng = random.Random(seed)
    n = len(x0)
    x = list(x0)
    meas = 0
    for k in range(rounds):
        ak = a / (k + 1 + 10) ** 0.602
        ck = c / (k + 1) ** 0.101
        delta = [1 if rng.random() < 0.5 else -1 for _ in range(n)]
        xp = [x[i] + ck * delta[i] for i in range(n)]
        xm = [x[i] - ck * delta[i] for i in range(n)]
        yp = measure(xp); meas += 1
        ym = measure(xm); meas += 1
        lp = sum((yp[i] - target[i]) ** 2 for i in range(n))
        lm = sum((ym[i] - target[i]) ** 2 for i in range(n))
        ghat = [(lp - lm) / (2 * ck * delta[i]) for i in range(n)]
        x = [x[i] - ak * ghat[i] for i in range(n)]
    yf = measure(x); meas += 1
    return x, yf, meas
