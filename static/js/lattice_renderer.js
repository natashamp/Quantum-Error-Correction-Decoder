/**
 * Canvas-based renderer for the surface code lattice.
 */
class LatticeRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.lattice = null;
        this.errors = [];
        this.syndrome = { x_defects: [], z_defects: [] };
        this.correction = [];
        this.cellSize = 40;
        this.padding = 50;
    }

    setLattice(latticeData) {
        this.lattice = latticeData;
        this.errors = [];
        this.syndrome = { x_defects: [], z_defects: [] };
        this.correction = [];
        this._resize();
        this.draw();
    }

    setErrors(errorList) {
        this.errors = errorList;
        this.draw();
    }

    setSyndrome(syndromeData) {
        this.syndrome = syndromeData;
        this.draw();
    }

    setCorrection(correctionList) {
        this.correction = correctionList;
        this.draw();
    }

    clear() {
        this.errors = [];
        this.syndrome = { x_defects: [], z_defects: [] };
        this.correction = [];
        this.draw();
    }

    _resize() {
        if (!this.lattice) return;
        const d = this.lattice.distance;
        const gridPx = (2 * d - 1) * this.cellSize;
        this.canvas.width = gridPx + 2 * this.padding;
        this.canvas.height = gridPx + 2 * this.padding;
    }

    _toPixel(row, col) {
        // Convert lattice coordinates to pixel coordinates
        // Data qubits are at (2r, 2c), stabilizers at odd coords
        const d = this.lattice.distance;
        const x = this.padding + col * this.cellSize / 2;
        const y = this.padding + row * this.cellSize / 2;
        return [x, y];
    }

    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Clear
        ctx.fillStyle = "#1a1a2e";
        ctx.fillRect(0, 0, w, h);

        if (!this.lattice) return;

        this._drawStabilizers();
        this._drawDataQubits();
        this._drawErrors();
        this._drawSyndrome();
        this._drawCorrection();
    }

    _drawStabilizers() {
        const ctx = this.ctx;
        const size = this.cellSize * 0.7;

        // X-stabilizers (blue, semi-transparent)
        ctx.fillStyle = "rgba(70, 130, 230, 0.2)";
        for (const [r, c] of this.lattice.x_stabilizers) {
            if (r < 0 || c < 0) continue; // skip boundary stabs in rendering
            const [x, y] = this._toPixel(r, c);
            ctx.fillRect(x - size / 2, y - size / 2, size, size);
        }

        // Z-stabilizers (red, semi-transparent)
        ctx.fillStyle = "rgba(230, 80, 80, 0.2)";
        for (const [r, c] of this.lattice.z_stabilizers) {
            if (r < 0 || c < 0) continue;
            const [x, y] = this._toPixel(r, c);
            ctx.fillRect(x - size / 2, y - size / 2, size, size);
        }
    }

    _drawDataQubits() {
        const ctx = this.ctx;
        const r = this.cellSize * 0.18;

        for (const [row, col] of this.lattice.data_qubits) {
            const [x, y] = this._toPixel(row, col);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = "#e0e0e0";
            ctx.fill();
            ctx.strokeStyle = "#888";
            ctx.lineWidth = 1;
            ctx.stroke();
        }
    }

    _drawErrors() {
        const ctx = this.ctx;
        const r = this.cellSize * 0.22;
        const colors = { X: "#ff4444", Z: "#4488ff", Y: "#cc44ff" };

        for (const err of this.errors) {
            const [x, y] = this._toPixel(err.pos[0], err.pos[1]);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = colors[err.pauli] || "#fff";
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();

            // Label
            ctx.fillStyle = "#fff";
            ctx.font = "bold 11px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(err.pauli, x, y);
        }
    }

    _drawSyndrome() {
        const ctx = this.ctx;

        // X-defects (blue diamonds)
        ctx.fillStyle = "#44aaff";
        for (const [r, c] of this.syndrome.x_defects) {
            const [x, y] = this._toPixel(r, c);
            ctx.beginPath();
            ctx.moveTo(x, y - 10);
            ctx.lineTo(x + 10, y);
            ctx.lineTo(x, y + 10);
            ctx.lineTo(x - 10, y);
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Z-defects (red diamonds)
        ctx.fillStyle = "#ff4444";
        for (const [r, c] of this.syndrome.z_defects) {
            const [x, y] = this._toPixel(r, c);
            ctx.beginPath();
            ctx.moveTo(x, y - 10);
            ctx.lineTo(x + 10, y);
            ctx.lineTo(x, y + 10);
            ctx.lineTo(x - 10, y);
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.stroke();
        }
    }

    _drawCorrection() {
        const ctx = this.ctx;
        const r = this.cellSize * 0.15;
        const colors = { X: "#ff8844", Z: "#44ccff", Y: "#ff44cc" };

        for (const corr of this.correction) {
            const [x, y] = this._toPixel(corr.pos[0], corr.pos[1]);

            // Draw a ring around the qubit
            ctx.beginPath();
            ctx.arc(x, y, r + 4, 0, Math.PI * 2);
            ctx.strokeStyle = colors[corr.pauli] || "#0f0";
            ctx.lineWidth = 3;
            ctx.setLineDash([4, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }
}
