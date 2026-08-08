# Box Trace Selector

Python symbolic verifier and MathJax browser UI for finite-dimensional
representation traces of the mixed tensor-spinor box operator.

## Quick start

Python 3.10 or newer is sufficient; the calculation code uses only the
standard library.

```bash
python KL_codex_handoff/generated/direct_box2_verification/trace_selector_web.py
```

On Windows, the launcher can be used instead:

```text
KL_codex_handoff\generated\direct_box2_verification\run_trace_selector.cmd
```

Then open `http://127.0.0.1:8765/` and select one of the eight fields and
either the `n=1` or `n=2` representation trace.

## Verification

```bash
cd KL_codex_handoff/generated/direct_box2_verification
python -m unittest -v test_verify_direct_box2.py test_trace_selector_web.py
python verify_direct_box2.py --verify-all
```

## Independent Cadabra/Jupyter calculator

The full `n=1`/`n=2` recalculation is also implemented independently for
Cadabra 2.5.14 in:

```text
KL_codex_handoff\generated\direct_box2_verification\cadabra
```

After the WSL environment is installed, double-click
`run_cadabra_jupyter.cmd`. It opens `full_trace_verification.ipynb`, whose
input cell sets `N` and the eight `(field, weight)` pairs. The notebook displays
the direct Box definition and every field-specialized Box, stores the fully
expanded weighted traces in `F1` through `F8`, and visibly executes
`totalTr = F1 + ... + F8` before Cadabra collects the exact residual. The
headless full test is:

```bash
cadabra2 -q verify_full_trace.cdb
```

The browser UI renders the fully expanded `n=2` results using ordinary
partial derivatives and Einstein-contracted background tensor indices. It
does not expose internal moment-basis or gamma-trace shorthand.

## Scope

- D=10 Majorana-Weyl spinor dimension 16
- density weight zero
- unprojected raw tensor products
- finite-dimensional representation trace before the coordinate functional
  trace and determinant prefactors

See `KL_codex_handoff/README_Codex.md` for the detailed conventions,
limitations, and output inventory.
