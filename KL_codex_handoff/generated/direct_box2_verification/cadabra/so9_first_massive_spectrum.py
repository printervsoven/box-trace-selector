"""Exact first-massive Type-II physical-spectrum checks in the SO(9) rest frame.

This module deliberately starts *after* the world-sheet BRST/GSO calculation.
The BRST cohomology at the first massive level of one chiral superstring is

    NS: Sym^2_0(V_9) + Lambda^3(V_9) = 44 + 84,
    R : ker(gamma: V_9 tensor S_16 -> S_16) = 128.

The functions below construct those weight systems and their physical
projectors exactly.  They then form the closed Type-II left/right spectrum and
audit its signed character (bosons minus fermions).  No floating-point
arithmetic and no raw, unprojected spinor-tensor surrogate is used.

Equivalently one could take a BRST Euler trace over the full matter-plus-ghost
complex, provided the insertion commutes with BRST and the regulator preserves
that cancellation.  These are two alternative descriptions of one trace, not
two contributions to add.

What this code directly proves is representation-theoretic: low *Cartan*
helicity supertraces of the physical first-massive multiplet vanish.  It does
not construct the complete world-sheet BRST differential, a gauge-fixed
spacetime Hessian, or string interaction vertices.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, permutations, product
from math import comb, factorial
from typing import Dict, Iterable, Iterator, Mapping, Sequence, Tuple


RANK = 4  # rank Spin(9) = rank B4
Weight = Tuple[Fraction, Fraction, Fraction, Fraction]
Character = Dict[Weight, int]
ZERO_WEIGHT: Weight = (Fraction(0),) * RANK


def _clean(character: Mapping[Weight, int]) -> Character:
    """Return a character without zero-multiplicity weights."""

    return {weight: int(mult) for weight, mult in character.items() if mult}


def _add_weights(left: Weight, right: Weight) -> Weight:
    return tuple(a + b for a, b in zip(left, right))  # type: ignore[return-value]


def add_characters(*terms: Tuple[int, Mapping[Weight, int]]) -> Character:
    """Add integer multiples of (possibly virtual) characters."""

    result: Dict[Weight, int] = defaultdict(int)
    for coefficient, character in terms:
        for weight, multiplicity in character.items():
            result[weight] += coefficient * multiplicity
    return _clean(result)


def tensor_product(left: Mapping[Weight, int], right: Mapping[Weight, int]) -> Character:
    """Weight character of a tensor product."""

    result: Dict[Weight, int] = defaultdict(int)
    for left_weight, left_mult in left.items():
        for right_weight, right_mult in right.items():
            result[_add_weights(left_weight, right_weight)] += left_mult * right_mult
    return _clean(result)


def character_dimension(character: Mapping[Weight, int]) -> int:
    """Character evaluated at the identity (signed for virtual characters)."""

    return sum(character.values())


def vector_weights() -> Tuple[Weight, ...]:
    """The nine one-dimensional weight spaces of the Spin(9) vector V_9."""

    weights = [ZERO_WEIGHT]
    for axis in range(RANK):
        for sign in (-1, 1):
            weight = [Fraction(0)] * RANK
            weight[axis] = Fraction(sign)
            weights.append(tuple(weight))
    return tuple(weights)


def spinor_weights() -> Tuple[Weight, ...]:
    """The sixteen weights (+-e1+-e2+-e3+-e4)/2 of the Spin(9) spinor."""

    return tuple(
        tuple(Fraction(sign, 2) for sign in signs)  # type: ignore[misc]
        for signs in product((-1, 1), repeat=RANK)
    )


def character_from_weight_spaces(weights: Iterable[Weight]) -> Character:
    result: Dict[Weight, int] = defaultdict(int)
    for weight in weights:
        result[weight] += 1
    return dict(result)


def symmetric_traceless_character() -> Character:
    """Character of Sym^2_0(V_9), obtained as Sym^2(V_9)-1."""

    basis = vector_weights()
    result: Dict[Weight, int] = defaultdict(int)
    for left in range(len(basis)):
        for right in range(left, len(basis)):
            result[_add_weights(basis[left], basis[right])] += 1
    result[ZERO_WEIGHT] -= 1  # remove the invariant metric trace
    return _clean(result)


def three_form_character() -> Character:
    """Character of Lambda^3(V_9)."""

    basis = vector_weights()
    result: Dict[Weight, int] = defaultdict(int)
    for indices in combinations(range(len(basis)), 3):
        weight = ZERO_WEIGHT
        for index in indices:
            weight = _add_weights(weight, basis[index])
        result[weight] += 1
    return dict(result)


def gamma_traceless_vector_spinor_character() -> Character:
    """Character of ker(V_9 tensor S_16 -> S_16), hence V*S-S."""

    vector = character_from_weight_spaces(vector_weights())
    spinor = character_from_weight_spaces(spinor_weights())
    return add_characters((1, tensor_product(vector, spinor)), (-1, spinor))


def physical_chiral_characters() -> Dict[str, Character]:
    """The physical first-massive chiral NS and R BRST cohomology."""

    rep44 = symmetric_traceless_character()
    rep84 = three_form_character()
    rep128 = gamma_traceless_vector_spinor_character()
    return {
        "44": rep44,
        "84": rep84,
        "128": rep128,
        "NS": add_characters((1, rep44), (1, rep84)),
        "R": rep128,
    }


def closed_type_ii_characters() -> Dict[str, Character]:
    """Four first-massive closed sectors and their signed physical character.

    On the diagonal massive little group Spin(9), Type IIA and Type IIB have
    the same character.  Their ten-dimensional Ramond chirality distinction
    does not define two inequivalent Spin(9) spinors.
    """

    chiral = physical_chiral_characters()
    ns, ramond = chiral["NS"], chiral["R"]
    sectors = {
        "NSNS": tensor_product(ns, ns),
        "RR": tensor_product(ramond, ramond),
        "NSR": tensor_product(ns, ramond),
        "RNS": tensor_product(ramond, ns),
    }
    sectors["signed"] = add_characters(
        (1, sectors["NSNS"]),
        (1, sectors["RR"]),
        (-1, sectors["NSR"]),
        (-1, sectors["RNS"]),
    )
    return sectors


def raw_eight_field_character() -> Character:
    """Scaled diagonal character of the old unprojected eight-field model.

    With all left/right raw spinor slots restricted to the same Spin(9), the
    integer-scaled weights are

      64 T + 8192 phi + 16 B_LL + 16 B_RR
      - 768 U_L - 768 U_R - U_LLR - U_LRR.

    Thus this is exactly 2(16-chi_16)^3.  It is retained only as a negative
    control; it is not substituted for the physical BRST cohomology.
    """

    spinor = character_from_weight_spaces(spinor_weights())
    spinor2 = tensor_product(spinor, spinor)
    spinor3 = tensor_product(spinor2, spinor)
    trivial = {ZERO_WEIGHT: 1}
    return add_characters(
        (64, spinor2),
        (8192, trivial),
        (16, spinor2),
        (16, spinor2),
        (-768, spinor),
        (-768, spinor),
        (-1, spinor3),
        (-1, spinor3),
    )


def raw_eight_field_factorised_character() -> Character:
    """The same raw virtual character, independently as 2(16-S)^3."""

    spinor = character_from_weight_spaces(spinor_weights())
    seed = add_characters((16, {ZERO_WEIGHT: 1}), (-1, spinor))
    return add_characters((2, tensor_product(tensor_product(seed, seed), seed)))


def signed_moment(character: Mapping[Weight, int], powers: Sequence[int]) -> Fraction:
    """Exact STr(J_1^p1 ... J_4^p4) from the weight character."""

    if len(powers) != RANK:
        raise ValueError(f"expected {RANK} Cartan powers")
    total = Fraction(0)
    for weight, multiplicity in character.items():
        monomial = Fraction(1)
        for component, power in zip(weight, powers):
            monomial *= component**power
        total += multiplicity * monomial
    return total


def _weak_compositions(total: int, length: int) -> Iterator[Tuple[int, ...]]:
    if length == 1:
        yield (total,)
        return
    for head in range(total + 1):
        for tail in _weak_compositions(total - head, length - 1):
            yield (head,) + tail


def moment_residuals(
    character: Mapping[Weight, int], degree_exclusive: int
) -> Dict[Tuple[int, ...], Fraction]:
    """Return every nonzero mixed moment of total degree below the cutoff."""

    # Every Spin(9) weight used here lies in (1/2) Z^4.  Accumulating the
    # numerator with ordinary Python integers and restoring 2^degree only at
    # the end is exactly equivalent to Fraction arithmetic, but makes the
    # exhaustive 3,876-moment closed-spectrum audit roughly two orders of
    # magnitude faster.
    scaled_weights = []
    for weight, multiplicity in character.items():
        doubled = tuple(2 * component for component in weight)
        if any(component.denominator != 1 for component in doubled):
            raise AssertionError("Spin(9) weight is not in the half-integral lattice")
        scaled_weights.append((tuple(int(component) for component in doubled), multiplicity))
    residuals: Dict[Tuple[int, ...], Fraction] = {}
    for total_degree in range(degree_exclusive):
        for powers in _weak_compositions(total_degree, RANK):
            numerator = 0
            for weight, multiplicity in scaled_weights:
                monomial = 1
                for component, power in zip(weight, powers):
                    monomial *= component**power
                numerator += multiplicity * monomial
            if numerator:
                residuals[powers] = Fraction(numerator, 2**total_degree)
    return residuals


def one_plane_laurent(character: Mapping[Weight, int]) -> Dict[int, int]:
    """Restrict to one rotation plane using z=exp(i*t/4).

    A weight w contributes z^(4w_1); all exponents are integral for Spin(9).
    """

    result: Dict[int, int] = defaultdict(int)
    for weight, multiplicity in character.items():
        exponent = 4 * weight[0]
        if exponent.denominator != 1:
            raise AssertionError("nonintegral Laurent exponent")
        result[int(exponent)] += multiplicity
    return {power: coefficient for power, coefficient in result.items() if coefficient}


def laurent_z_minus_inverse(power: int, coefficient: int = 1) -> Dict[int, int]:
    """Laurent expansion of coefficient*(z-z^-1)^power."""

    return {
        power - 2 * chosen_inverse: coefficient
        * (-1) ** chosen_inverse
        * comb(power, chosen_inverse)
        for chosen_inverse in range(power + 1)
    }


def character_audit() -> Dict[str, object]:
    """Return exact dimensions, factorisations, and low-moment checks."""

    chiral = physical_chiral_characters()
    closed = closed_type_ii_characters()
    raw = raw_eight_field_character()
    physical_laurent = one_plane_laurent(closed["signed"])
    raw_laurent = one_plane_laurent(raw)
    return {
        "dimensions": {name: character_dimension(char) for name, char in chiral.items()},
        "sector_dimensions": {
            name: character_dimension(closed[name])
            for name in ("NSNS", "RR", "NSR", "RNS")
        },
        "closed_signed_dimension": character_dimension(closed["signed"]),
        "open_moments_below_8": moment_residuals(
            add_characters((1, chiral["NS"]), (-1, chiral["R"])), 8
        ),
        "closed_moments_below_16": moment_residuals(closed["signed"], 16),
        "physical_one_plane_factor": physical_laurent
        == laurent_z_minus_inverse(16),
        "raw_direct_equals_factorised": raw == raw_eight_field_factorised_character(),
        "raw_one_plane_factor": raw_laurent
        == laurent_z_minus_inverse(6, coefficient=-1024),
        "raw_equals_physical": raw == closed["signed"],
        "first_open_moment": signed_moment(
            add_characters((1, chiral["NS"]), (-1, chiral["R"])), (8, 0, 0, 0)
        ),
        "expected_first_open_moment": Fraction(factorial(8), 256),
        "first_closed_moment": signed_moment(closed["signed"], (16, 0, 0, 0)),
        "expected_first_closed_moment": Fraction(factorial(16), 65536),
    }


@dataclass(frozen=True)
class ProjectorDiagnostics:
    name: str
    ambient_dimension: int
    trace: int
    expected_trace: int
    idempotent: bool
    constraints_hold: bool

    @property
    def passed(self) -> bool:
        return (
            self.trace == self.expected_trace
            and self.idempotent
            and self.constraints_hold
        )


def symmetric_traceless_projector_diagnostics(dimension: int = 9) -> ProjectorDiagnostics:
    """Build P_ij,kl = delta_i(k delta_l)j - delta_ij delta_kl/d exactly."""

    import sympy as sp

    ambient = dimension * dimension
    projector = sp.zeros(ambient, ambient)
    for i, j, k, ell in product(range(dimension), repeat=4):
        projector[i * dimension + j, k * dimension + ell] = (
            sp.Rational(1, 2)
            * (int(i == k and j == ell) + int(i == ell and j == k))
            - sp.Rational(1, dimension) * int(i == j) * int(k == ell)
        )
    idempotent = projector * projector == projector
    symmetric_output = all(
        projector[i * dimension + j, column]
        == projector[j * dimension + i, column]
        for i, j in product(range(dimension), repeat=2)
        for column in range(ambient)
    )
    traceless_output = all(
        sum(projector[i * dimension + i, column] for i in range(dimension)) == 0
        for column in range(ambient)
    )
    return ProjectorDiagnostics(
        name="Sym^2_0(V_9)",
        ambient_dimension=ambient,
        trace=int(projector.trace()),
        expected_trace=dimension * (dimension + 1) // 2 - 1,
        idempotent=idempotent,
        constraints_hold=symmetric_output and traceless_output,
    )


def _permutation_sign(order: Sequence[int]) -> int:
    inversions = sum(
        order[left] > order[right]
        for left in range(len(order))
        for right in range(left + 1, len(order))
    )
    return -1 if inversions % 2 else 1


def _antisymmetrise_basis_triple(indices: Tuple[int, int, int]) -> Dict[Tuple[int, int, int], Fraction]:
    output: Dict[Tuple[int, int, int], Fraction] = defaultdict(Fraction)
    for order in permutations(range(3)):
        permuted = tuple(indices[index] for index in order)
        output[permuted] += Fraction(_permutation_sign(order), factorial(3))
    return {key: value for key, value in output.items() if value}


def _apply_three_form_projector(
    tensor: Mapping[Tuple[int, int, int], Fraction]
) -> Dict[Tuple[int, int, int], Fraction]:
    output: Dict[Tuple[int, int, int], Fraction] = defaultdict(Fraction)
    for indices, coefficient in tensor.items():
        for projected, projected_coefficient in _antisymmetrise_basis_triple(indices).items():
            output[projected] += coefficient * projected_coefficient
    return {key: value for key, value in output.items() if value}


def three_form_projector_diagnostics(dimension: int = 9) -> ProjectorDiagnostics:
    """Check the complete sparse 3-index antisymmetriser on all d^3 basis tensors."""

    trace = Fraction(0)
    idempotent = True
    alternating = True
    for indices in product(range(dimension), repeat=3):
        projected = _antisymmetrise_basis_triple(indices)
        trace += projected.get(indices, Fraction(0))
        idempotent = idempotent and _apply_three_form_projector(projected) == projected
        if projected:
            swapped = _antisymmetrise_basis_triple((indices[1], indices[0], indices[2]))
            alternating = alternating and swapped == {
                key: -value for key, value in projected.items()
            }
    return ProjectorDiagnostics(
        name="Lambda^3(V_9)",
        ambient_dimension=dimension**3,
        trace=int(trace),
        expected_trace=comb(dimension, 3),
        idempotent=idempotent,
        constraints_hold=alternating,
    )


def _spin9_gamma_matrices():
    """An exact 16x16 Euclidean Clifford(9) representation."""

    import sympy as sp

    identity = sp.eye(2)
    sigma1 = sp.Matrix([[0, 1], [1, 0]])
    sigma2 = sp.Matrix([[0, -sp.I], [sp.I, 0]])
    sigma3 = sp.diag(1, -1)

    def kron(factors):
        result = sp.Matrix([[1]])
        for factor in factors:
            result = sp.kronecker_product(result, factor)
        return result

    gammas = []
    for position in range(RANK):
        prefix = [sigma3] * position
        suffix = [identity] * (RANK - position - 1)
        gammas.append(kron(prefix + [sigma1] + suffix))
        gammas.append(kron(prefix + [sigma2] + suffix))
    gammas.append(kron([sigma3] * RANK))
    return tuple(gammas)


def gamma_traceless_projector_diagnostics(dimension: int = 9) -> ProjectorDiagnostics:
    """Check P_ij=delta_ij-(1/d) gamma_i gamma_j block by block."""

    import sympy as sp

    if dimension != 9:
        raise ValueError("the supplied Clifford representation is specifically Spin(9)")
    gammas = _spin9_gamma_matrices()
    spinor_dimension = gammas[0].rows
    zero = sp.zeros(spinor_dimension)
    identity = sp.eye(spinor_dimension)
    clifford = all(
        gammas[i] * gammas[j] + gammas[j] * gammas[i]
        == 2 * int(i == j) * identity
        for i, j in product(range(dimension), repeat=2)
    )
    blocks = [
        [
            int(i == j) * identity
            - sp.Rational(1, dimension) * gammas[i] * gammas[j]
            for j in range(dimension)
        ]
        for i in range(dimension)
    ]
    gamma_trace = all(
        sum((gammas[i] * blocks[i][j] for i in range(dimension)), zero) == zero
        for j in range(dimension)
    )
    idempotent = all(
        sum((blocks[i][k] * blocks[k][j] for k in range(dimension)), zero)
        == blocks[i][j]
        for i, j in product(range(dimension), repeat=2)
    )
    trace = sum(sp.trace(blocks[i][i]) for i in range(dimension))
    return ProjectorDiagnostics(
        name="ker(gamma: V_9 tensor S_16 -> S_16)",
        ambient_dimension=dimension * spinor_dimension,
        trace=int(trace),
        expected_trace=(dimension - 1) * spinor_dimension,
        idempotent=idempotent,
        constraints_hold=clifford and gamma_trace,
    )


def projector_audit() -> Dict[str, ProjectorDiagnostics]:
    return {
        "44": symmetric_traceless_projector_diagnostics(),
        "84": three_form_projector_diagnostics(),
        "128": gamma_traceless_projector_diagnostics(),
    }


def run_acceptance() -> None:
    characters = character_audit()
    projectors = projector_audit()
    assert characters["dimensions"] == {
        "44": 44,
        "84": 84,
        "128": 128,
        "NS": 128,
        "R": 128,
    }
    assert characters["sector_dimensions"] == {
        "NSNS": 16384,
        "RR": 16384,
        "NSR": 16384,
        "RNS": 16384,
    }
    assert characters["closed_signed_dimension"] == 0
    assert characters["open_moments_below_8"] == {}
    assert characters["closed_moments_below_16"] == {}
    assert characters["physical_one_plane_factor"] is True
    assert characters["raw_direct_equals_factorised"] is True
    assert characters["raw_one_plane_factor"] is True
    assert characters["raw_equals_physical"] is False
    assert characters["first_open_moment"] == characters["expected_first_open_moment"]
    assert characters["first_closed_moment"] == characters["expected_first_closed_moment"]
    assert all(diagnostics.passed for diagnostics in projectors.values())

    print("PASS physical chiral cohomology: 44 + 84 bosons; 128 fermions")
    print("PASS closed sectors: 16384 states each; 32768 B + 32768 F")
    print("PASS P44/P84/P128: exact trace, constraints, and P^2=P")
    print("PASS Z_open(t) = 256 sin(t/4)^8")
    print("PASS Z_TypeII(t) = 65536 sin(t/4)^16")
    print("PASS mixed Cartan helicity supertraces: degree < 16 vanish exactly")
    print("PASS negative control: Z_raw != Z_TypeII")


if __name__ == "__main__":
    run_acceptance()
