"""
Analysis tools: Monte Carlo simulation, threshold scans, and benchmarks.
"""

import time
import numpy as np

from qec.lattice import SurfaceCodeLattice
from qec.noise import apply_noise
from qec.syndrome import extract_syndrome, check_logical_error


def monte_carlo(lattice, decoder, noise_model, p, num_trials,
                rng=None, **noise_kwargs):
    """Run Monte Carlo simulation to estimate logical error rate.

    Returns:
        dict with logical_error_rate, std_error, num_trials, avg_runtime_ms
    """
    if rng is None:
        rng = np.random.default_rng()

    failures = 0
    total_time = 0.0

    for _ in range(num_trials):
        errors = apply_noise(lattice, noise_model, p, rng=rng, **noise_kwargs)
        syndrome = extract_syndrome(lattice, errors)

        t0 = time.perf_counter()
        correction = decoder.decode(lattice, syndrome)
        total_time += time.perf_counter() - t0

        result = check_logical_error(lattice, errors, correction)
        if result["is_error"]:
            failures += 1

    rate = failures / num_trials
    std_error = np.sqrt(rate * (1 - rate) / num_trials) if num_trials > 0 else 0

    return {
        "logical_error_rate": rate,
        "std_error": std_error,
        "num_trials": num_trials,
        "avg_runtime_ms": (total_time / num_trials * 1000) if num_trials > 0 else 0,
    }


def threshold_scan(distances, p_values, decoder_class, noise_model,
                   num_trials_per_point, rng=None, **noise_kwargs):
    """Scan over distances and error rates to produce threshold plot data.

    Args:
        distances: list of code distances (e.g., [3, 5, 7, 9])
        p_values: list of physical error rates
        decoder_class: decoder class (will be instantiated)
        noise_model: noise model name
        num_trials_per_point: trials per (d, p) point
        rng: random generator

    Returns:
        dict: {d: {p: {"logical_error_rate": ..., "std_error": ...}}}
    """
    if rng is None:
        rng = np.random.default_rng()

    decoder = decoder_class()
    results = {}

    for d in distances:
        results[d] = {}
        lattice = SurfaceCodeLattice(d)

        for p in p_values:
            mc = monte_carlo(
                lattice, decoder, noise_model, p, num_trials_per_point,
                rng=rng, **noise_kwargs,
            )
            results[d][p] = mc
            print(f"d={d}, p={p:.3f}: rate={mc['logical_error_rate']:.4f} "
                  f"± {mc['std_error']:.4f} "
                  f"({mc['avg_runtime_ms']:.2f} ms/trial)")

    return results


def benchmark_decoders(decoder_classes, distances, p, num_trials, rng=None):
    """Compare decoder runtimes as a function of code distance.

    Returns:
        dict: {decoder_name: {d: avg_time_ms}}
    """
    if rng is None:
        rng = np.random.default_rng()

    results = {}

    for dec_class in decoder_classes:
        decoder = dec_class()
        name = decoder.name()
        results[name] = {}

        for d in distances:
            lattice = SurfaceCodeLattice(d)
            mc = monte_carlo(lattice, decoder, "depolarizing", p, num_trials, rng=rng)
            results[name][d] = mc["avg_runtime_ms"]
            print(f"{name} d={d}: {mc['avg_runtime_ms']:.3f} ms/trial, "
                  f"rate={mc['logical_error_rate']:.4f}")

    return results


def plot_threshold(scan_results, title="Threshold Plot", save_path=None):
    """Generate a threshold plot from scan results.

    Args:
        scan_results: output of threshold_scan
        title: plot title
        save_path: if provided, save plot to this path
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))

    for d in sorted(scan_results.keys()):
        p_vals = sorted(scan_results[d].keys())
        rates = [scan_results[d][p]["logical_error_rate"] for p in p_vals]
        errors = [scan_results[d][p]["std_error"] for p in p_vals]
        ax.errorbar(p_vals, rates, yerr=errors, marker="o",
                    label=f"d={d}", capsize=3)

    ax.set_xlabel("Physical error rate (p)")
    ax.set_ylabel("Logical error rate")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved plot to {save_path}")

    plt.close(fig)
    return fig
