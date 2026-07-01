# TrueLoop measurement-efficiency reproduction

A self-contained benchmark that reproduces, on the **live TrueLoop endpoint**, the
core measurement-efficiency result: under drift at an equal measurement budget, the
TrueLoop runtime holds a multi-channel output at a setpoint far tighter than
finite-difference and SPSA gradient methods, and the advantage widens with the
channel count.

The full method, protocol, and limits are in [`TrueLoop_Collaboration_Brief.pdf`](./TrueLoop_Collaboration_Brief.pdf).

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

## Going to scale (up to N = 100,000)

The hosted endpoint supports channel counts up to N = 4096. To reproduce the large-N
results, run the same scripts against a **licensed offline build** (the same runtime,
compiled, no cap). Unzip your build, point `PYTHONPATH` at it, flip one variable:

```bash
export TRUELOOP_BACKEND=offline
export PYTHONPATH=/path/to/trueloop_offline      # folder containing the 'trueloop' package
python scale_regulation.py --plant cos2 --sizes 1024,10000,100000
```

Three extra scripts, all backend-agnostic (endpoint for N<=4096, offline for any N):

- **`scale_regulation.py`** — setpoint-holding tracking RMS as N grows. Shows the RMS is
  essentially **constant in N** (the runtime holds a 100,000-channel device as tightly as
  a small one), because it spends one measurement per update regardless of N.
- **`plant_variations.py`** — the same holding across physically distinct device responses
  (periodic, linear, saturating, non-smooth). Confirms setpoint-holding is a property of the
  runtime, not of one plant shape. It is model-free: the response shape is never supplied.
- **`kpi_summary.py`** — translates the result into measurement efficiency: acquisitions to
  regulate the device. The runtime reaches target in a small, **N-independent** number of
  acquisitions; finite difference needs N+1 acquisitions for a single update. At N=100,000
  that is on the order of **10,000x fewer measurements**. The script prints the honest
  reading of this number, and the things not to do with it.

These are simulated plants. Real-hardware transfer is the load-bearing validation step, the
same as for every claim here.

## What crosses the wire

Only a configuration vector and a scalar score per round. Your raw measurements stay
on your machine. The update law runs server-side (endpoint) or inside the licensed compiled
build (offline) and is never exposed in source form.

## Files

| file | role | edit? |
|------|------|-------|
| `plant.py` | the device interface (simulated by default) | **yes — to use hardware** |
| `benchmark.py` | the endpoint reproduction script | no |
| `baselines.py` | classical comparison controllers (finite-difference, SPSA) | no |
| `swc_runtime/` | the TrueLoop client (thin HTTP shim) | no |
| `swc_backend.py` | runs the scale scripts on endpoint OR offline build | no |
| `plants.py` | simulated device responses for the scale/variation demos | no |
| `scale_regulation.py` | setpoint-holding RMS vs N, up to 100,000 | no |
| `plant_variations.py` | holding across distinct device response shapes | no |
| `kpi_summary.py` | measurement-efficiency KPI (with honesty guardrails) | no |

## Configuration (environment variables, all optional)

| var | default | meaning |
|-----|---------|---------|
| `TRUELOOP_KEY` | — | your evaluation key (required for the endpoint backend) |
| `TRUELOOP_BACKEND` | `endpoint` | `endpoint` (N<=4096) or `offline` (licensed build, any N) |
| `PYTHONPATH` | — | for the offline backend: folder containing the `trueloop` package |
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
