# Surface Code Quantum Error Correction Decoder

A from-scratch Python implementation of a surface code simulator with two QEC decoders (MWPM and Union-Find) and an interactive browser-based visualization.

## What This Project Does

Quantum computers are extremely sensitive to noise. Quantum Error Correction (QEC) encodes a single **logical qubit** into many **physical qubits**, then uses **decoders** to identify and correct errors from noisy syndrome measurements.

This project simulates the full QEC pipeline for the **rotated surface code**:

1. **Lattice construction** -- builds a distance-d rotated surface code with d^2 data qubits and d^2 - 1 stabilizer checks
2. **Error injection** -- applies configurable noise models (depolarizing, bit-flip, phase-flip, biased)
3. **Syndrome extraction** -- measures which stabilizers detect errors
4. **Decoding** -- two decoders infer corrections from the syndrome:
   - **MWPM (Minimum Weight Perfect Matching)** -- exact DP-based matching, optimal for the surface code
   - **Union-Find** -- cluster growth + peeling decoder, near-linear time
5. **Logical error checking** -- determines if the correction succeeded or introduced a logical error
6. **Analysis** -- Monte Carlo sampling, threshold plots, runtime benchmarks

## Project Structure

```
qec/
  lattice.py            # Rotated surface code lattice
  noise.py              # Noise models (depolarizing, bit-flip, phase-flip, biased)
  syndrome.py           # Syndrome extraction + logical error check
  decoder_base.py       # Abstract decoder interface
  mwpm_decoder.py       # MWPM decoder (exact DP matching from scratch)
  unionfind_decoder.py  # Union-Find decoder (cluster growth + peeling)
  analysis.py           # Monte Carlo, threshold scans, benchmarks

server/
  app.py                # Flask application
  routes.py             # REST API endpoints

static/
  index.html            # Browser visualization
  css/style.css         # Styling
  js/                   # Canvas renderer, controls, API client

tests/                  # 30 unit tests

run_server.py           # Launch the visualization (opens browser)
run_analysis.py         # CLI for threshold scans and benchmarks
```

## Setup

```bash
# Install dependencies (only numpy, flask, matplotlib)
pip install -r requirements.txt
```

## How to Run

### Interactive Visualization

```bash
python run_server.py
```

Opens a browser at `http://localhost:5000` with:
- Canvas rendering of the qubit lattice with color-coded errors, syndromes, and corrections
- Controls for distance, noise model, error rate, and decoder selection
- Side-by-side decoder comparison
- Monte Carlo trial runner

### Threshold Analysis (CLI)

```bash
# Default: MWPM decoder, d=3,5,7, depolarizing noise, 1000 trials/point
python run_analysis.py

# Custom scan
python run_analysis.py --distances 3,5,7,9 --p-min 0.01 --p-max 0.12 --trials 2000 --decoder mwpm

# Decoder benchmark
python run_analysis.py --benchmark --distances 3,5,7,9,11
```

Outputs a threshold plot (`threshold_plot.png`) showing logical error rate vs physical error rate for each code distance. The crossing point of the curves is the **error threshold** (~10% for MWPM on depolarizing noise).

### Run Tests

```bash
pytest tests/ -v
```

## Key Results

MWPM decoder on depolarizing noise (1000 trials per point):

| | p = 0.02 | p = 0.05 | p = 0.08 |
|---|---|---|---|
| **d = 3** | 9.0% | 19.4% | 34.2% |
| **d = 5** | 1.0% | 6.6% | 12.5% |
| **d = 7** | 0.5% | 5.1% | 13.0% |

Below threshold, the logical error rate decreases exponentially with code distance -- demonstrating that QEC works.

## How the Decoders Work

### MWPM Decoder

1. Builds a **syndrome graph**: nodes are defects (fired stabilizers) + virtual boundary, edges weighted by Chebyshev distance on the rotated lattice
2. Finds the **minimum weight perfect matching** using exact DP with bitmask (O(n^2 * 2^n), practical for n < 24 defects)
3. Traces **diagonal correction paths** between matched defect pairs, flipping data qubits along the way

### Union-Find Decoder

1. Initializes each defect as an odd-parity cluster on the stabilizer graph
2. **Grows clusters** by processing edges iteratively -- merges when at least one cluster has odd parity
3. Stops when all clusters have even parity (defects are paired, possibly with the boundary)
4. **Peels** the spanning forest: removes leaves, flipping edges where syndromes are active

## Dependencies

- `numpy` -- array operations for error/correction vectors
- `flask` -- web server for the visualization
- `matplotlib` -- static threshold plots
