# First-massive Type-II physical-spectrum audit

`so9_first_massive_spectrum.py` is an exact, independent check of the actual
first-massive physical representation in the massive rest frame.  It does not
reuse the eight raw spinor-tensor fields or their trace ledgers.

## BRST/GSO boundary

The world-sheet BRST/GSO calculation is used at one clearly marked boundary:
its physical cohomology at one chiral first-massive level is

\[
\mathcal H_{\mathrm{NS}}=\mathrm{Sym}^2_0(V_9)\oplus\Lambda^3(V_9),
\qquad
\mathcal H_{\mathrm R}=\ker\!\left(
\gamma:V_9\otimes S_{16}\longrightarrow S_{16}\right).
\]

The module constructs these cohomology spaces, rather than reconstructing the
full world-sheet ghost complex.  There are two legitimate, alternative routes
to the same physical trace:

1. trace over the BRST cohomology, as this module does; or
2. take the graded Euler trace over the full matter-plus-ghost BRST complex.

The second route equals the first by quartet/Euler cancellation only when the
inserted operator commutes with the BRST differential and the trace or
regulator respects that cancellation.  The two routes must **not** be added;
doing so would count the same physical states twice.

In an on-shell rest frame, transversality has already removed the time-like
polarization.  The remaining exact projectors are

\[
(P_{44})_{ij,kl}
=\frac12(\delta_{ik}\delta_{jl}+\delta_{il}\delta_{jk})
-\frac19\delta_{ij}\delta_{kl},
\]

\[
P_{84}=\frac1{3!}\sum_{\sigma\in S_3}
\operatorname{sgn}(\sigma)\,\sigma,
\qquad
(P_{128})_{i\alpha,j\beta}
=\delta_{ij}\delta_{\alpha\beta}
-\frac19(\gamma_i\gamma_j)_{\alpha\beta}.
\]

The acceptance test builds these projectors over exact rationals (and an exact
16 by 16 Clifford(9) representation) and verifies

\[
P_r^2=P_r,
\qquad
\operatorname{tr}P_{44}=44,
\quad
\operatorname{tr}P_{84}=84,
\quad
\operatorname{tr}P_{128}=128.
\]

It separately checks symmetry/tracelessness, complete antisymmetry, and
gamma-tracelessness.

## Closed Type-II character

Let

\[
\chi_{\mathrm{NS}}=\chi_{44}+\chi_{84},
\qquad
\chi_{\mathrm R}=\chi_{128}.
\]

The four closed sectors are constructed as literal left/right tensor products.
Their dimensions are

| sector | dimension | statistics |
|---|---:|---|
| NS-NS | 16,384 | bosonic |
| R-R | 16,384 | bosonic |
| NS-R | 16,384 | fermionic |
| R-NS | 16,384 | fermionic |

Consequently the physical signed character is

\[
Z_{\mathrm{II}}
=(\chi_{\mathrm{NS}}-\chi_{\mathrm R})_L
\times(\chi_{\mathrm{NS}}-\chi_{\mathrm R})_R.
\]

For a rotation by `t` in one little-group plane, the program proves the exact
Laurent-polynomial identities

\[
Z_{\mathrm{open}}(t)=256\sin^8\frac t4,
\qquad
Z_{\mathrm{II}}(t)=65536\sin^{16}\frac t4.
\]

It also enumerates every mixed Cartan helicity moment and verifies

\[
\operatorname{STr}_{\mathrm{open}}J_1^{p_1}\cdots J_4^{p_4}=0
\quad (p_1+\cdots+p_4<8),
\]

\[
\operatorname{STr}_{\mathrm{II}}J_1^{p_1}\cdots J_4^{p_4}=0
\quad (p_1+\cdots+p_4<16).
\]

The computation directly proves these statements only for mutually commuting
Cartan generators.  There is a precise representation-theory extension: the
fully symmetrised tensor

\[
d^{(k)}_{a_1\ldots a_k}
=\operatorname{STr}J_{(a_1}\cdots J_{a_k)}
\]

is an invariant symmetric polynomial on \(\mathfrak{so}(9)\).  Injectivity of
the Chevalley restriction from invariant polynomials to the Cartan subalgebra
therefore implies \(d^{(k)}=0\) for \(k<16\).  PBW symmetrisation then rewrites
an ordered noncommuting word as its symmetrised word plus shorter commutator
words; recursively, their representation supertraces also vanish below degree
16.  This last step is an algebraic corollary, not a noncommuting-word
enumeration performed by the code.

Turning either statement into a claim about a spacetime `Box` still requires
proving that the gauge-fixed physical/ghost Hessian uses this same
representation action, that its insertion is BRST-compatible, and that no
field-dependent projectors or coefficients invalidate the reduction.

## Required negative control

The old eight-field model, with its weights multiplied by 64, has diagonal
character

\[
Z_{\mathrm{raw}}=2(16-\chi_{16})^3
=65536\sin^6\frac t4.
\]

The test constructs this once from all eight weighted raw fields and once from
the factorised expression.  It proves those two raw expressions agree, and
then proves

\[
Z_{\mathrm{raw}}\ne Z_{\mathrm{II}}.
\]

Thus equal total boson/fermion counts and some low raw moments are not treated
as an identification with the physical Type-II spectrum.

## Run

From this directory in WSL:

```bash
python3 -m unittest -v test_so9_first_massive_spectrum.py
python3 so9_first_massive_spectrum.py
cadabra2 -q verify_so9_physical_spectrum.cdb
```

The first two commands require SymPy.  The third command is intentionally a
thin wrapper which invokes the **same** Python module inside a Cadabra kernel.
It verifies environment compatibility; it is not an independent Cadabra
derivation of the character or projectors.

## Spectrum reference

The imported BRST/GSO cohomology and its physical polarizations are documented
in the following primary sources:

- N. Agia, *Massive Type IIB Superstrings Part I: 3- and 4-Point Amplitudes*,
  [arXiv:2309.11538](https://arxiv.org/abs/2309.11538).  Its first-massive RNS
  vertex operators exhibit the NS symmetric-traceless tensor and three-form,
  and the R gamma-traceless vector-spinor used here.
- N. Berkovits and O. Chandia, *Massive Superstring Vertex Operator in D=10
  Superspace*,
  [arXiv:hep-th/0204121](https://arxiv.org/abs/hep-th/0204121).  This gives a
  covariant pure-spinor construction of the same first-massive open-string
  supermultiplet.
