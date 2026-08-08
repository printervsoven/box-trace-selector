# Cadabra2 full Box-trace verification

This directory contains a self-contained Cadabra2/Jupyter recalculation of the
fully expanded finite-dimensional representation traces for `n=1` and `n=2`.
It does not import the existing Python verifier, renderer, CSV files, or their
precomputed term lists.

## Environment

The tested environment is:

- Windows 11 host
- WSL2 with Ubuntu 24.04
- Cadabra 2.5.14
- Jupyter Notebook using the `Cadabra2` kernel

If Cadabra is not installed, run `install_cadabra_wsl.sh` as root inside the
Ubuntu-24.04 WSL distribution. Then double-click `run_cadabra_jupyter.cmd` and
keep its terminal open. Jupyter is bound to `127.0.0.1`; keep token
authentication enabled.

## Main files

- `full_trace_calculator.cdb` — independent full expansion engine and public
  Box-display, field-variable, trace, and cancellation functions.
- `full_trace_verification.ipynb` — interactive calculator. Its default cells
  display the direct Box definition, all eight field-specialized Boxes, all
  1,994 weighted field rows, and all 404 cancellation identities.
- `verify_full_trace.cdb` — headless acceptance suite, including an independent
  Cadabra gamma-algebra comparison and a perturbed-weight negative control.
- `box2_verification.ipynb` and `verify_box2_smoke.cdb` — the earlier compact
  first-stage smoke checks.

## Interactive use

Open `full_trace_verification.ipynb` with the Cadabra2 kernel. The visible
workflow is:

```python
show_box_definition()
show_field_boxes(FIELD_COMBINATION)

PREPARED = prepare_field_variables(FIELD_COMBINATION, N)
F1, F2, F3, F4, F5, F6, F7, F8 = PREPARED.weighted_expressions

totalTr = F1 + F2 + F3 + F4 + F5 + F6 + F7 + F8
distribute(totalTr)
canonicalise(totalTr)
collect_terms(totalTr)
assert totalTr == 0
```

The input cell contains `N` and the eight explicit `(field, weight)` tuples,
so both can be edited before the later cells are run. `prepare_field_variables`
prints every fully Einstein-contracted term before storing the weighted
Cadabra expressions in `F1` through `F8`.

`trace_terms` accepts `T`, `phi`, `BLL`, `BRR`, `UL`, `UR`, `ULLR`, `ULRR`,
and the four-field representations `B`, `U`, `chi`. Only `n=1` and `n=2` are
implemented; other values fail explicitly.

One overall weight multiplies each field's complete trace. Individual tensor
terms do not receive independently chosen weights.

## Headless verification

Run from this directory inside WSL:

```bash
cadabra2 -q verify_full_trace.cdb
```

Acceptance goldens:

- universal `n=1`: 9 ordered blocks / 23 coefficient primitives;
- universal `n=2`: 118 ordered blocks / 867 coefficient primitives;
- eight fields, `n=2`: 1,994 expanded rows -> 404 complete tensor bodies ->
  404/404 exact zeros -> Cadabra residual `0`;
- four fields, `n=2`: 1,404 expanded rows -> 404 complete tensor bodies ->
  404/404 exact zeros -> Cadabra residual `0`;
- changing one weight from `-1/64` to `-1/63` leaves 404 nonzero residuals.

The suite also has Cadabra independently evaluate traces of two, three, and
four bivector gamma matrices. Their complete 2/8/60 metric-pairing maps agree
coefficient-by-coefficient with the standalone recursion used by the engine.

## What “full expansion” means

The engine starts from the single-Box coefficient blocks, composes ordered
differential operators with the complete Leibniz rule, expands total
generators into raw left/right spinor slots, applies the right-sector reversal
and `-1/2` normalization (displayed as the transpose action on each
`bar S*` slot), evaluates every chiral Clifford trace, and absorbs
all local metrics into explicit upper/lower Einstein dummy indices. Final rows
contain only the paper-level `H`, `Gamma`, `Phi`, barred `Phi`, curvature and
ordinary-partial notation; no covariant-D, total-generator, gamma-trace, eta,
or moment shorthand remains.

Cadabra receives every weighted final row before `collect_terms` is called.
The notebook displays a `K0001...K0404` audit label for each complete tensor
body and prints the exact field-by-field rational coefficient sum together
with the full body represented by that label.

## Scope and caveat

This proves coefficientwise cancellation for D=10, `dim S=dim Sbar=16`,
density weight zero, unprojected raw tensor products, and a common universal
background/operator. It is a finite-dimensional representation trace before
the functional/momentum trace.

It does not by itself include irreducible projections, field-dependent masses,
statistics, chirality/reality/Pfaffian normalisations, gauge fixing, ghosts, or
the regulator. The same numerical relative weights also cancel the algebraic
`n=1` representation trace, but physical one-loop `n=1` determinant weights
may differ because their mass powers and other prefactors are n-dependent.
