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
  define every coefficient, sign, and coefficient-tensor body in main.pdf
  equations (2.1), (2.2), and (2.6) as one executable `BOX_INPUT`, then
  display all eight field-specialized Boxes,
  all 1,994 weighted field rows, and all 404 cancellation identities.
- `verify_full_trace.cdb` — headless acceptance suite, including an independent
  Cadabra gamma-algebra comparison and a perturbed-weight negative control.
- `box2_verification.ipynb` and `verify_box2_smoke.cdb` — the earlier compact
  first-stage smoke checks.

## Interactive use

Open `full_trace_verification.ipynb` with the Cadabra2 kernel. The visible
workflow starts from an executable input object, not a display-only formula:

```python
DELTA_RICCI_BODY_INPUT = BoxTensorBody(
    name="main Ricci",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("Ricci", ("pair1",)),
    )),),
)
DELTA_CONNECTION_BODY_INPUT = BoxTensorBody(
    name="main connection",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("GammaUp", ("coordinate", "pair1")),
    )),),
)
DELTA_GENERATOR_SQUARE_BODY_INPUT = BoxTensorBody(
    name="main connection square",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("GammaDown", ("coordinate", "pair1")),
        TensorBodyFactor("GammaUp", ("coordinate", "pair2")),
    )),),
)
DELTA_MIXED_CURVATURE_BODY_INPUT = BoxTensorBody(
    name="main mixed curvature",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("MixedCurvature", ("left_pair", "right_pair")),
    )),),
)

# Separate barDelta objects make a one-sector edit unambiguous.
BAR_DELTA_RICCI_BODY_INPUT = BoxTensorBody(
    name="main Ricci",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("Ricci", ("pair1",)),
    )),),
)
BAR_DELTA_CONNECTION_BODY_INPUT = BoxTensorBody(
    name="main connection",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("GammaUp", ("coordinate", "pair1")),
    )),),
)
BAR_DELTA_GENERATOR_SQUARE_BODY_INPUT = BoxTensorBody(
    name="main connection square",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("GammaDown", ("coordinate", "pair1")),
        TensorBodyFactor("GammaUp", ("coordinate", "pair2")),
    )),),
)
BAR_DELTA_MIXED_CURVATURE_BODY_INPUT = BoxTensorBody(
    name="main mixed curvature",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("MixedCurvature", ("left_pair", "right_pair")),
    )),),
)

BOX_INPUT = MainBoxDefinition(
    delta=DeltaDefinition(
        laplacian=Fraction(1),
        ricci_generator=Fraction(1),
        connection_derivative_generator=Fraction(-1),
        generator_square=Fraction(1, 4),
        mixed_curvature_generators=Fraction(1, 2),
        ricci_body=DELTA_RICCI_BODY_INPUT,
        connection_body=DELTA_CONNECTION_BODY_INPUT,
        generator_square_body=DELTA_GENERATOR_SQUARE_BODY_INPUT,
        mixed_curvature_body=DELTA_MIXED_CURVATURE_BODY_INPUT,
    ),
    bar_delta=DeltaDefinition(
        laplacian=Fraction(1),
        ricci_generator=Fraction(1),
        connection_derivative_generator=Fraction(-1),
        generator_square=Fraction(1, 4),
        mixed_curvature_generators=Fraction(1, 2),
        ricci_body=BAR_DELTA_RICCI_BODY_INPUT,
        connection_body=BAR_DELTA_CONNECTION_BODY_INPUT,
        generator_square_body=BAR_DELTA_GENERATOR_SQUARE_BODY_INPUT,
        mixed_curvature_body=BAR_DELTA_MIXED_CURVATURE_BODY_INPUT,
    ),
    delta_in_box=Fraction(1),
    bar_delta_in_box=Fraction(-1),
)

FIELD_BOX_DEFINITIONS = {
    field: BOX_INPUT for field, _weight in FIELD_COMBINATION
}
show_box_definition(box_definition=BOX_INPUT)
show_field_boxes(
    FIELD_COMBINATION,
    box_definition=BOX_INPUT,
    field_box_definitions=FIELD_BOX_DEFINITIONS,
)

PREPARED = prepare_field_variables(
    FIELD_COMBINATION,
    N,
    box_definition=BOX_INPUT,
    field_box_definitions=FIELD_BOX_DEFINITIONS,
)
F1, F2, F3, F4, F5, F6, F7, F8 = PREPARED.weighted_expressions

totalTr = F1 + F2 + F3 + F4 + F5 + F6 + F7 + F8
distribute(totalTr)
canonicalise(totalTr)
collect_terms(totalTr)
assert totalTr == 0
```

The first code cell contains all five coefficients for each of `Delta` and
`barDelta`, eight sector-specific typed coefficient-tensor bodies, and the two signs/weights in
`Box = Delta - barDelta`. `BoxTensorBody` is the calculation AST and its LaTeX
is generated from those same factors; there is no display-only duplicate.
`Riemann(pair1,pair2)` treats each Lorentz pair as antisymmetric but assumes
neither pair-exchange symmetry nor a Bianchi identity.
Later input cells contain `N` and the eight explicit `(field, weight)` tuples.
All of these can be edited before the later cells are run. `prepare_field_variables`
prints every fully Einstein-contracted term before storing the weighted
Cadabra expressions in `F1` through `F8`. Those variables contain the actual
internal `H`, `Gamma`, `Phi`, `BarPhi`, `Rfrak`, and derivative tensor ASTs;
`K0001...` labels are never used inside the expressions. Their registered
LaTeX heads display as `\mathcal H`, `\Gamma`, `\Phi`, `\bar\Phi`,
`\mathfrak R`, and `\partial`, so printing `F1;` exposes no internal English
head names. External right-acting derivatives are contracted `ExtD` factors
rendered directly as `\partial_A`, so every Cadabra term remains a scalar
without displaying an auxiliary probe field.

`trace_terms` accepts `T`, `phi`, `BLL`, `BRR`, `UL`, `UR`, `ULLR`, `ULRR`,
and the four-field representations `B`, `U`, `chi`. Only `n=1` and `n=2` are
implemented; other values fail explicitly.

One overall weight multiplies each field's complete trace. Individual tensor
terms do not receive independently chosen weights.

The notebook finishes with a structural negative control. It replaces
`GammaDown(B,pair1)*GammaUp(B,pair2)` by `Riemann(pair1,pair2)` only in the
`T`-field copy and sends that mapping through the same preparation, explicit
`F1 + ... + F8`, canonicalisation, and collection path:

```python
RIEMANN_SQUARE_BODY_INPUT = BoxTensorBody(
    name="Riemann replacement",
    monomials=(TensorBodyMonomial(1, (
        TensorBodyFactor("Riemann", ("pair1", "pair2")),
    )),),
)
MODIFIED_T_BOX = BOX_INPUT.with_body(
    "delta", "generator_square", RIEMANN_SQUARE_BODY_INPUT
)
MODIFIED_FIELD_BOX_DEFINITIONS = dict(FIELD_BOX_DEFINITIONS)
MODIFIED_FIELD_BOX_DEFINITIONS["T"] = MODIFIED_T_BOX

MODIFIED_PREPARED = prepare_field_variables(
    FIELD_COMBINATION,
    N,
    box_definition=BOX_INPUT,
    field_box_definitions=MODIFIED_FIELD_BOX_DEFINITIONS,
    show=False,
)
# The notebook then constructs and collects totalTr_modified explicitly.
assert totalTr_modified != 0
```

This field-specific mismatch is intentional. Applying the same modified Box to
all eight fields can still give zero: the selected weights separately annihilate
the six raw-slot representation moments, independently of the common Box
operator structures. A nonzero result from a common modification would
therefore be a bug, not a stronger negative control. The T-only structural
replacement produces 1,987 pre-collection summands and leaves 107 nonzero
coefficient rows / 91 Cadabra-canonical residual tensor structures.

## DFT background geometry objects

The notebook's final section displays the immutable `main.pdf` background
objects used by the trace engine:

```python
GammaDFT = get_dft_object("Gamma")   # main.pdf (3.7)
RDFT = get_dft_object("R")           # main.pdf (3.10)

GAMMA_CONNECTED = show_dft_object(
    GammaDFT, calculations=(PREPARED, MODIFIED_PREPARED)
)
R_CONNECTED = show_dft_object(
    RDFT, calculations=(PREPARED, MODIFIED_PREPARED)
)
```

Their renderers show the complete DFT-Christoffel definition, curvature
definition, local `Gamma_Cpq`, raised `Gamma^C_pq`, and `R_pqrs` projections,
plus the curvature antisymmetry, Ricci contraction, and semi-covariant `S`
definition. The `CONNECTED` audit walks the live trace rows and requires the
calculation factors to reference the same `TensorHeadDefinition` objects used
by these renderers; it is not a display-string comparison.

The current trace expansion keeps `Gamma` and `Rfrak` as background
primitives. It does not substitute equations (3.7) and (3.10) into every row
and re-expand them into `P`, `barP`, and `d`. `R_pqrs` uses antisymmetry inside
each index pair only; pair-exchange symmetry and Bianchi identities are not
assumed.

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
- a common executable-Box deformation still cancels, while a T-only Box
  coefficient deformation leaves 9 ledger rows / 5 Cadabra-canonical
  structures;
- the common GammaGamma-to-Riemann structural replacement still cancels,
  while the T-only replacement leaves 107 ledger rows / 91 Cadabra structures;
- changing one weight from `-1/64` to `-1/63` leaves all 404 conservative
  ledger rows nonzero (358 structures after Cadabra also identifies commuting
  derivative/dummy-index equivalences).

The suite also has Cadabra independently evaluate traces of two, three, and
four bivector gamma matrices. Their complete 2/8/60 metric-pairing maps agree
coefficient-by-coefficient with the standalone recursion used by the engine.

## What “full expansion” means

The displayed calculation starts directly from main.pdf equations (2.1),
(2.2), and (2.6). Total-generator actions are shown component by component as
the field specialisations of equations (2.3) and (2.4), without introducing
`A_X`, `B_X`, `h`, `u`, `b`, or slot-labelled gamma shorthand. For the actual
ordinary-partial expansion the engine privately normal-orders those same
main.pdf terms, composes the differential operators with the complete Leibniz
rule, expands total generators into raw left/right spinor slots, applies the
right-sector reversal and `-1/2` normalization, evaluates every chiral
Clifford trace, and absorbs all local metrics into explicit upper/lower
Einstein dummy indices. Final rows contain only the paper-level `H`, `Gamma`,
`Phi`, barred `Phi`, curvature and ordinary-partial notation; no covariant-D,
total-generator, gamma-trace, eta, or moment shorthand remains.

Cadabra receives every weighted final tensor expression before `collect_terms`
is called. The notebook separately displays a `K0001...K0404` audit row number
for each complete tensor body and prints the exact field-by-field rational
coefficient sum together with the full body represented by that row number.
These row numbers are presentation metadata only and do not occur in `F1`–`F8`.

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
