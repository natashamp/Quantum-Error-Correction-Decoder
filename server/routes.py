"""REST API routes for the QEC decoder visualization."""

import time
import numpy as np
from flask import jsonify, request, send_from_directory

from qec.lattice import SurfaceCodeLattice
from qec.noise import apply_noise
from qec.syndrome import extract_syndrome, check_logical_error
from qec.mwpm_decoder import MWPMDecoder
from qec.unionfind_decoder import UnionFindDecoder
from qec.analysis import monte_carlo

# Server-side state (single-user local tool)
state = {
    "lattice": None,
    "errors": None,
    "syndrome": None,
    "correction": None,
    "rng": np.random.default_rng(),
}

DECODERS = {
    "mwpm": MWPMDecoder,
    "unionfind": UnionFindDecoder,
}


def register_routes(app):

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/lattice", methods=["POST"])
    def create_lattice():
        data = request.get_json()
        d = data.get("distance", 3)
        try:
            state["lattice"] = SurfaceCodeLattice(d)
            state["errors"] = None
            state["syndrome"] = None
            state["correction"] = None
            return jsonify({"status": "ok", "lattice": state["lattice"].to_dict()})
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/api/inject_errors", methods=["POST"])
    def inject_errors():
        if state["lattice"] is None:
            return jsonify({"status": "error", "message": "No lattice"}), 400

        data = request.get_json()
        model = data.get("model", "depolarizing")
        p = data.get("p", 0.05)
        seed = data.get("seed")

        if seed is not None:
            state["rng"] = np.random.default_rng(seed)

        state["errors"] = apply_noise(
            state["lattice"], model, p, rng=state["rng"],
            **{k: v for k, v in data.items() if k not in ("model", "p", "seed")}
        )
        state["syndrome"] = None
        state["correction"] = None

        L = state["lattice"]
        error_list = []
        for i, e in enumerate(state["errors"]):
            if e:
                pauli = {1: "X", 2: "Z", 3: "Y"}[int(e)]
                error_list.append({
                    "pos": list(L.data_qubits[i]),
                    "pauli": pauli,
                    "index": i,
                })

        return jsonify({"status": "ok", "errors": error_list})

    @app.route("/api/extract_syndrome", methods=["POST"])
    def api_extract_syndrome():
        if state["lattice"] is None or state["errors"] is None:
            return jsonify({"status": "error", "message": "No lattice or errors"}), 400

        state["syndrome"] = extract_syndrome(state["lattice"], state["errors"])
        state["correction"] = None

        return jsonify({
            "status": "ok",
            "syndrome": {
                "x_defects": [list(d) for d in state["syndrome"]["x_defects"]],
                "z_defects": [list(d) for d in state["syndrome"]["z_defects"]],
            },
        })

    @app.route("/api/decode", methods=["POST"])
    def decode():
        if state["lattice"] is None or state["syndrome"] is None:
            return jsonify({"status": "error", "message": "No syndrome"}), 400

        data = request.get_json()
        decoder_name = data.get("decoder", "mwpm")
        decoder_cls = DECODERS.get(decoder_name)
        if decoder_cls is None:
            return jsonify({"status": "error", "message": f"Unknown decoder: {decoder_name}"}), 400

        decoder = decoder_cls()
        L = state["lattice"]

        t0 = time.perf_counter()
        state["correction"] = decoder.decode(L, state["syndrome"])
        elapsed_ms = (time.perf_counter() - t0) * 1000

        correction_list = []
        for i, c in enumerate(state["correction"]):
            if c:
                pauli = {1: "X", 2: "Z", 3: "Y"}[int(c)]
                correction_list.append({
                    "pos": list(L.data_qubits[i]),
                    "pauli": pauli,
                    "index": i,
                })

        result = check_logical_error(L, state["errors"], state["correction"])

        return jsonify({
            "status": "ok",
            "correction": correction_list,
            "logical_error": result,
            "decoder": decoder_name,
            "runtime_ms": round(elapsed_ms, 3),
        })

    @app.route("/api/compare", methods=["POST"])
    def compare():
        """Run both decoders and return side-by-side results."""
        if state["lattice"] is None or state["syndrome"] is None:
            return jsonify({"status": "error", "message": "No syndrome"}), 400

        L = state["lattice"]
        results = {}

        for name, cls in DECODERS.items():
            decoder = cls()
            t0 = time.perf_counter()
            correction = decoder.decode(L, state["syndrome"])
            elapsed_ms = (time.perf_counter() - t0) * 1000

            correction_list = []
            for i, c in enumerate(correction):
                if c:
                    pauli = {1: "X", 2: "Z", 3: "Y"}[int(c)]
                    correction_list.append({
                        "pos": list(L.data_qubits[i]),
                        "pauli": pauli,
                    })

            result = check_logical_error(L, state["errors"], correction)

            results[name] = {
                "correction": correction_list,
                "logical_error": result,
                "runtime_ms": round(elapsed_ms, 3),
            }

        return jsonify({"status": "ok", "results": results})

    @app.route("/api/run_trials", methods=["POST"])
    def run_trials():
        """Run Monte Carlo trials."""
        data = request.get_json()
        d = data.get("distance", 3)
        p = data.get("p", 0.05)
        model = data.get("model", "depolarizing")
        decoder_name = data.get("decoder", "mwpm")
        num_trials = min(data.get("num_trials", 100), 10000)

        decoder_cls = DECODERS.get(decoder_name)
        if decoder_cls is None:
            return jsonify({"status": "error", "message": f"Unknown decoder"}), 400

        lattice = SurfaceCodeLattice(d)
        decoder = decoder_cls()
        result = monte_carlo(lattice, decoder, model, p, num_trials, rng=state["rng"])

        return jsonify({"status": "ok", **result, "decoder": decoder_name,
                        "distance": d, "p": p, "model": model})
