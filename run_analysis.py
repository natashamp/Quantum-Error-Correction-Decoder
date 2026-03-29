"""CLI for running threshold scans and benchmarks."""

import argparse
import numpy as np
from qec.mwpm_decoder import MWPMDecoder
from qec.unionfind_decoder import UnionFindDecoder
from qec.analysis import threshold_scan, benchmark_decoders, plot_threshold


DECODERS = {"mwpm": MWPMDecoder, "unionfind": UnionFindDecoder}


def main():
    parser = argparse.ArgumentParser(description="QEC Decoder Analysis")
    parser.add_argument("--distances", default="3,5,7",
                        help="Comma-separated code distances")
    parser.add_argument("--p-min", type=float, default=0.01)
    parser.add_argument("--p-max", type=float, default=0.15)
    parser.add_argument("--p-step", type=float, default=0.01)
    parser.add_argument("--trials", type=int, default=1000)
    parser.add_argument("--decoder", default="mwpm", choices=DECODERS.keys())
    parser.add_argument("--noise", default="depolarizing")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="threshold_plot.png")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run decoder benchmark instead of threshold scan")
    args = parser.parse_args()

    distances = [int(d) for d in args.distances.split(",")]
    rng = np.random.default_rng(args.seed)

    if args.benchmark:
        print("Running decoder benchmark...")
        results = benchmark_decoders(
            list(DECODERS.values()), distances, 0.05, args.trials, rng=rng
        )
        print("\nResults:")
        for name, data in results.items():
            print(f"  {name}: {data}")
    else:
        p_values = list(np.arange(args.p_min, args.p_max + args.p_step / 2, args.p_step))
        print(f"Threshold scan: d={distances}, p={p_values[0]:.2f}-{p_values[-1]:.2f}, "
              f"{args.trials} trials/point, decoder={args.decoder}")

        results = threshold_scan(
            distances, p_values, DECODERS[args.decoder],
            args.noise, args.trials, rng=rng,
        )
        plot_threshold(results, title=f"Threshold: {args.decoder.upper()}", save_path=args.output)


if __name__ == "__main__":
    main()
