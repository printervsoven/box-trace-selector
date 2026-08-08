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
