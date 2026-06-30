# TrueLoop measurement-efficiency reproduction

A self-contained benchmark that reproduces, on the **live TrueLoop endpoint**, the
core measurement-efficiency result: under drift at an equal measurement budget, the
TrueLoop runtime holds a multi-channel output at a setpoint far tighter than
finite-difference and SPSA gradient methods, and the advantage widens with the
channel count.

It runs **out of the box on a simulated plant**, and is built so you can **swap in
your real hardware by editing one file**.

---

## What you need

- Python 3.8+ (standard library only; no numpy required to run the benchmark).
- A free 90-day evaluation key: **https://compute.neophotonics.ca/**
  (also reachable at https://trueloopcompute.com/ — the `compute.neophotonics.ca`
  mirror is provided because it clears common university network filters.)

## Run it (simulated plant, ~2 minutes)

```bash
pip install ./swc_runtime
export TRUELOOP_KEY=EVAL-xxxxxxxxxxxxxxxxxxxxxxxx
python benchmark.py
```

You should see SWC tracking RMS stay low and roughly flat as `n` grows from 8 to
256, while the gradient baselines climb — their per-update measurement cost (n+1 for
finite-difference, 2 for SPSA) eats the equal budget under drift.

## Run it on YOUR hardware

Edit **`plant.py`** — only the two marked functions:

- `apply(x)` — write the control vector `x` to your device.
- `measure(x)` — apply `x`, read your detector(s), return an N-vector in `[0,1]^N`.

Nothing else changes. The runtime learns each channel's sign, gain, and shape from
measurement, so you do **not** need to calibrate or model the device. The only
requirement is that each channel's output moves consistently (locally monotonic)
when you move its control over your operating range.

```bash
# after editing plant.py:
python benchmark.py
```

## What crosses the wire

Only a configuration vector and a scalar score per round. Your raw measurements stay
on your machine. The update law runs server-side and is never downloaded.

## Files

| file | role | edit? |
|------|------|-------|
| `plant.py` | the device interface (simulated by default) | **yes — to use hardware** |
| `benchmark.py` | the reproduction script | no |
| `baselines.py` | classical comparison controllers | no |
| `swc_runtime/` | the TrueLoop client (thin HTTP shim) | no |

## Configuration (environment variables, all optional)

| var | default | meaning |
|-----|---------|---------|
| `TRUELOOP_KEY` | — | your evaluation key (required) |
| `TRUELOOP_ENDPOINT` | `https://compute.neophotonics.ca` | the endpoint |
| `TRUELOOP_SIZES` | `8,32,128,256` | channel counts to sweep |
| `TRUELOOP_ROUNDS` | `80` | measurement budget |
| `TRUELOOP_DRIFT` | `0.15` | plant drift rate (simulated plant only) |

## Output

A table to stdout and `results.json` with the tracking RMS for each method at each
`n`. Drop your own `results.json` into the figure scripts, or just read the table.

---

Questions, or a result that does not reproduce on your hardware? That is exactly what
we want to hear about: **matthew@trueloopcompute.com**.
