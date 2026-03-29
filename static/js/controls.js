/**
 * UI control wiring for the QEC visualization.
 */
class Controls {
    constructor(renderer, statusEl) {
        this.renderer = renderer;
        this.statusEl = statusEl;
        this._bindEvents();
    }

    setStatus(msg) {
        this.statusEl.textContent = msg;
    }

    _bindEvents() {
        document.getElementById("btn-create").addEventListener("click", () => this.createLattice());
        document.getElementById("btn-inject").addEventListener("click", () => this.injectErrors());
        document.getElementById("btn-syndrome").addEventListener("click", () => this.extractSyndrome());
        document.getElementById("btn-decode").addEventListener("click", () => this.decode());
        document.getElementById("btn-compare").addEventListener("click", () => this.compare());
        document.getElementById("btn-reset").addEventListener("click", () => this.reset());
        document.getElementById("btn-auto").addEventListener("click", () => this.autoRun());
        document.getElementById("btn-trials").addEventListener("click", () => this.runTrials());

        // Update p display
        const pSlider = document.getElementById("p-slider");
        const pValue = document.getElementById("p-value");
        pSlider.addEventListener("input", () => {
            pValue.textContent = pSlider.value;
        });
    }

    async createLattice() {
        const d = parseInt(document.getElementById("distance").value);
        this.setStatus(`Creating d=${d} lattice...`);
        const resp = await postAPI("lattice", { distance: d });
        if (resp.status === "ok") {
            this.renderer.setLattice(resp.lattice);
            this.setStatus(`Lattice created: d=${d}, ${resp.lattice.data_qubits.length} data qubits`);
        } else {
            this.setStatus(`Error: ${resp.message}`);
        }
    }

    async injectErrors() {
        const model = document.getElementById("noise-model").value;
        const p = parseFloat(document.getElementById("p-slider").value);
        this.setStatus(`Injecting ${model} noise (p=${p})...`);
        const resp = await postAPI("inject_errors", { model, p });
        if (resp.status === "ok") {
            this.renderer.setErrors(resp.errors);
            this.renderer.setSyndrome({ x_defects: [], z_defects: [] });
            this.renderer.setCorrection([]);
            this.setStatus(`Injected: ${resp.errors.length} errors`);
            this._clearResults();
        }
    }

    async extractSyndrome() {
        this.setStatus("Extracting syndrome...");
        const resp = await postAPI("extract_syndrome");
        if (resp.status === "ok") {
            this.renderer.setSyndrome(resp.syndrome);
            const nx = resp.syndrome.x_defects.length;
            const nz = resp.syndrome.z_defects.length;
            this.setStatus(`Syndrome: ${nx} X-defects, ${nz} Z-defects`);
        }
    }

    async decode() {
        const decoder = document.getElementById("decoder").value;
        this.setStatus(`Decoding with ${decoder.toUpperCase()}...`);
        const resp = await postAPI("decode", { decoder });
        if (resp.status === "ok") {
            this.renderer.setCorrection(resp.correction);
            this._showResult(resp.decoder, resp);
        }
    }

    async compare() {
        this.setStatus("Comparing decoders...");
        const resp = await postAPI("compare");
        if (resp.status === "ok") {
            // Show MWPM correction on the canvas
            if (resp.results.mwpm) {
                this.renderer.setCorrection(resp.results.mwpm.correction);
            }
            this._showCompareResults(resp.results);
        }
    }

    async autoRun() {
        await this.injectErrors();
        await this.extractSyndrome();
        await this.compare();
    }

    async runTrials() {
        const d = parseInt(document.getElementById("distance").value);
        const p = parseFloat(document.getElementById("p-slider").value);
        const model = document.getElementById("noise-model").value;
        const decoder = document.getElementById("decoder").value;
        const n = parseInt(document.getElementById("num-trials").value);

        this.setStatus(`Running ${n} trials (d=${d}, p=${p}, ${decoder})...`);
        const resp = await postAPI("run_trials", {
            distance: d, p, model, decoder, num_trials: n,
        });
        if (resp.status === "ok") {
            const rate = (resp.logical_error_rate * 100).toFixed(2);
            const se = (resp.std_error * 100).toFixed(2);
            const rt = resp.avg_runtime_ms.toFixed(2);
            this.setStatus(`${n} trials: logical error rate = ${rate}% (${se}%), avg ${rt} ms/trial`);
            document.getElementById("trials-result").textContent =
                `Rate: ${rate}% \u00B1 ${se}% | Avg time: ${rt} ms`;
        }
    }

    reset() {
        this.renderer.clear();
        this._clearResults();
        this.setStatus("Reset. Click 'New Error' to start.");
    }

    _showResult(name, data) {
        const el = document.getElementById("decode-result");
        const logErr = data.logical_error.is_error ? "YES" : "No";
        const color = data.logical_error.is_error ? "#ff4444" : "#44ff44";
        el.innerHTML = `<strong>${name.toUpperCase()}</strong>: ` +
            `${data.correction.length} corrections, ` +
            `<span style="color:${color}">${logErr} logical error</span>, ` +
            `${data.runtime_ms} ms`;
    }

    _showCompareResults(results) {
        const el = document.getElementById("decode-result");
        let html = "";
        for (const [name, data] of Object.entries(results)) {
            const logErr = data.logical_error.is_error ? "YES" : "No";
            const color = data.logical_error.is_error ? "#ff4444" : "#44ff44";
            html += `<div><strong>${name.toUpperCase()}</strong>: ` +
                `${data.correction.length} corrections, ` +
                `<span style="color:${color}">${logErr} logical error</span>, ` +
                `${data.runtime_ms} ms</div>`;
        }
        el.innerHTML = html;
        this.setStatus("Comparison complete");
    }

    _clearResults() {
        document.getElementById("decode-result").innerHTML = "";
        document.getElementById("trials-result").textContent = "";
    }
}
