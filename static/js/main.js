/**
 * App entry point — initializes renderer and controls.
 */
document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("lattice-canvas");
    const statusEl = document.getElementById("status");

    const renderer = new LatticeRenderer(canvas);
    const controls = new Controls(renderer, statusEl);

    // Auto-create a d=3 lattice on load
    controls.createLattice();
});
