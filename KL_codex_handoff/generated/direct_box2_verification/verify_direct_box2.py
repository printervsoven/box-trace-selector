from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from collections import defaultdict
from typing import Dict, Tuple, List, Iterable, Sequence
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

OUTDIR = os.path.dirname(os.path.abspath(__file__))

@dataclass(frozen=True, order=True)
class Factor:
    kind: str
    indices: Tuple[str, ...]
    derivs: Tuple[str, ...] = ()

    def derivative(self, idx: str) -> "Factor":
        # Partial derivatives commute; sort the derivative labels canonically.
        return Factor(self.kind, self.indices, tuple(sorted(self.derivs + (idx,))))

    def text(self) -> str:
        base = f"{self.kind}[{','.join(self.indices)}]"
        if self.derivs:
            return f"d({','.join(self.derivs)}){base}"
        return base

Monomial = Tuple[Factor, ...]

class Expr:
    def __init__(self, terms: Dict[Monomial, Fraction] | None = None):
        self.terms: Dict[Monomial, Fraction] = defaultdict(Fraction)
        if terms:
            for m, c in terms.items():
                if c:
                    self.terms[tuple(sorted(m))] += Fraction(c)
        self._cleanup()

    @staticmethod
    def one() -> "Expr":
        return Expr({(): Fraction(1)})

    @staticmethod
    def factor(f: Factor, coeff: Fraction = Fraction(1)) -> "Expr":
        return Expr({(f,): coeff})

    def copy(self) -> "Expr":
        return Expr(dict(self.terms))

    def _cleanup(self):
        dead = [m for m, c in self.terms.items() if c == 0]
        for m in dead:
            del self.terms[m]

    def __add__(self, other: "Expr") -> "Expr":
        out = self.copy()
        for m, c in other.terms.items():
            out.terms[m] += c
        out._cleanup()
        return out

    def __sub__(self, other: "Expr") -> "Expr":
        return self + (-other)

    def __neg__(self) -> "Expr":
        return Expr({m: -c for m, c in self.terms.items()})

    def __mul__(self, other: "Expr" | Fraction | int) -> "Expr":
        if isinstance(other, (int, Fraction)):
            return Expr({m: c * Fraction(other) for m, c in self.terms.items()})
        out: Dict[Monomial, Fraction] = defaultdict(Fraction)
        for m1, c1 in self.terms.items():
            for m2, c2 in other.terms.items():
                out[tuple(sorted(m1 + m2))] += c1 * c2
        return Expr(out)

    def __rmul__(self, other: Fraction | int) -> "Expr":
        return self * other

    def derivative(self, idx: str) -> "Expr":
        out: Dict[Monomial, Fraction] = defaultdict(Fraction)
        for mon, coeff in self.terms.items():
            for pos, fac in enumerate(mon):
                new_mon = list(mon)
                new_mon[pos] = fac.derivative(idx)
                out[tuple(sorted(new_mon))] += coeff
        return Expr(out)

    def second_derivative(self, i: str, j: str) -> "Expr":
        return self.derivative(j).derivative(i)

    def term_count(self) -> int:
        return len(self.terms)

    def serialize(self) -> List[dict]:
        rows = []
        for mon, coeff in sorted(self.terms.items(), key=lambda kv: tuple(f.text() for f in kv[0])):
            rows.append({
                "coeff_num": coeff.numerator,
                "coeff_den": coeff.denominator,
                "factors": [f.text() for f in mon],
            })
        return rows

class Fresh:
    def __init__(self):
        self.n = 0
    def reset(self):
        self.n = 0
    def idx(self, stem: str) -> str:
        self.n += 1
        return f"{stem}{self.n}"

fresh = Fresh()

def F(kind: str, *indices: str, derivs: Sequence[str] = ()) -> Expr:
    return Expr.factor(Factor(kind, tuple(indices), tuple(sorted(derivs))))

def H(a: str, b: str) -> Expr:
    return F("H", a, b)

def dH(a: str, b: str, *ds: str) -> Expr:
    return F("H", a, b, derivs=ds)

def GammaABC(a: str, b: str, c: str) -> Expr:
    return F("GammaABC", a, b, c)

def GammaLUp(c: str, i: str) -> Expr:
    return F("GammaLUp", c, i)

def GammaRUp(c: str, j: str) -> Expr:
    return F("GammaRUp", c, j)

def GammaLDown(a: str, i: str) -> Expr:
    return F("GammaLDown", a, i)

def GammaRDown(a: str, j: str) -> Expr:
    return F("GammaRDown", a, j)

def Phi(a: str, i: str) -> Expr:
    return F("Phi", a, i)

def BarPhi(a: str, j: str) -> Expr:
    return F("BarPhi", a, j)

def RicL(i: str) -> Expr:
    return F("RicL", i)

def RicR(j: str) -> Expr:
    return F("RicR", j)

def MixRL(j: str, i: str) -> Expr:
    return F("MixRL", j, i)

def MixLR(i: str, j: str) -> Expr:
    return F("MixLR", i, j)

# Coefficient blocks. Each call creates fresh dummy indices to avoid accidental collisions.
def block_h(c: str) -> Expr:
    m, n = fresh.idx("m"), fresh.idx("n")
    return H(m, n) * GammaABC(m, n, c)

def block_u(c: str, i: str) -> Expr:
    m = fresh.idx("m")
    return H(c, m) * Phi(m, i) - GammaLUp(c, i)

def block_v(c: str, j: str) -> Expr:
    m = fresh.idx("m")
    return H(c, m) * BarPhi(m, j) + GammaRUp(c, j)

def block_p(i: str) -> Expr:
    m, n, c = fresh.idx("m"), fresh.idx("n"), fresh.idx("c")
    return (RicL(i)
            + Fraction(1,2) * H(m,n) * Phi(n,i).derivative(m)
            + Fraction(1,2) * H(m,n) * GammaABC(m,n,c) * Phi(c,i))

def block_q(j: str) -> Expr:
    m, n, c = fresh.idx("m"), fresh.idx("n"), fresh.idx("c")
    return (-RicR(j)
            + Fraction(1,2) * H(m,n) * BarPhi(n,j).derivative(m)
            + Fraction(1,2) * H(m,n) * GammaABC(m,n,c) * BarPhi(c,j))

def block_r(i: str, k: str) -> Expr:
    m, n, c, a = fresh.idx("m"), fresh.idx("n"), fresh.idx("c"), fresh.idx("a")
    return (Fraction(1,4) * H(m,n) * Phi(m,i) * Phi(n,k)
            - Fraction(1,2) * GammaLUp(c,i) * Phi(c,k)
            + Fraction(1,4) * GammaLDown(a,i) * GammaLUp(a,k))

def block_s(j: str, l: str) -> Expr:
    m, n, c, a = fresh.idx("m"), fresh.idx("n"), fresh.idx("c"), fresh.idx("a")
    return (Fraction(1,4) * H(m,n) * BarPhi(m,j) * BarPhi(n,l)
            + Fraction(1,2) * GammaRUp(c,j) * BarPhi(c,l)
            - Fraction(1,4) * GammaRDown(a,j) * GammaRUp(a,l))

def block_t(i: str, j: str) -> Expr:
    m, n, c1, c2 = fresh.idx("m"), fresh.idx("n"), fresh.idx("c"), fresh.idx("c")
    return (Fraction(1,2) * H(m,n) * Phi(m,i) * BarPhi(n,j)
            - Fraction(1,2) * GammaLUp(c1,i) * BarPhi(c1,j)
            + Fraction(1,2) * GammaRUp(c2,j) * Phi(c2,i)
            + Fraction(1,2) * MixRL(j,i)
            - Fraction(1,2) * MixLR(i,j))

@dataclass
class Component:
    name: str
    kind: str  # A0, AL, AR, BL, BR, BLL, BRR, BLR

# component constructors return coefficient expr and word [(sector,label), ...]
def A_component(kind: str, c: str, label_counter: List[int]) -> Tuple[Expr, Tuple[Tuple[str,str], ...], str]:
    if kind == "A0":
        return block_h(c), (), "h"
    if kind == "AL":
        label_counter[0] += 1; i = f"I{label_counter[0]}"
        return block_u(c,i), (("L",i),), "u"
    if kind == "AR":
        label_counter[1] += 1; j = f"J{label_counter[1]}"
        return block_v(c,j), (("R",j),), "v"
    raise ValueError(kind)

def B_component(kind: str, label_counter: List[int]) -> Tuple[Expr, Tuple[Tuple[str,str], ...], str]:
    if kind == "BL":
        label_counter[0] += 1; i = f"I{label_counter[0]}"
        return block_p(i), (("L",i),), "p"
    if kind == "BR":
        label_counter[1] += 1; j = f"J{label_counter[1]}"
        return block_q(j), (("R",j),), "q"
    if kind == "BLL":
        label_counter[0] += 1; i = f"I{label_counter[0]}"
        label_counter[0] += 1; k = f"I{label_counter[0]}"
        return block_r(i,k), (("L",i),("L",k)), "r"
    if kind == "BRR":
        label_counter[1] += 1; j = f"J{label_counter[1]}"
        label_counter[1] += 1; l = f"J{label_counter[1]}"
        return block_s(j,l), (("R",j),("R",l)), "s"
    if kind == "BLR":
        label_counter[0] += 1; i = f"I{label_counter[0]}"
        label_counter[1] += 1; j = f"J{label_counter[1]}"
        return block_t(i,j), (("L",i),("R",j)), "t"
    raise ValueError(kind)

A_KINDS = ["A0","AL","AR"]
B_KINDS = ["BL","BR","BLL","BRR","BLR"]

@dataclass
class ExactTerm:
    term_id: str
    source: str
    derivative_order: int
    derivative_indices: Tuple[str, ...]
    coefficient: Expr
    word: Tuple[Tuple[str,str], ...]
    block_signature: str


def generate_n1_terms() -> List[ExactTerm]:
    """Generate the nine universal terms in Box before taking the trace.

    The operator power corresponds to n=1 in the log-determinant expansion,
    but this function constructs only the finite-dimensional representation
    trace data, not its functional trace or determinant prefactor.  The value
    of n is distinct from the generator-word length.
    """
    fresh.reset()
    terms: List[ExactTerm] = []
    tid = 0

    def add(source, order, deriv_indices, coeff, word, sig):
        nonlocal tid
        tid += 1
        terms.append(ExactTerm(f"N1T{tid:02d}", source, order, tuple(deriv_indices), coeff, tuple(word), sig))

    a, b, c = "A", "B", "C"
    add("H d2", 2, (a, b), H(a, b), (), "H")
    for ak in A_KINDS:
        lc = [0, 0]
        ac, word, name = A_component(ak, c, lc)
        add("A d1", 1, (c,), ac, word, name)
    for bk in B_KINDS:
        lc = [0, 0]
        be, word, name = B_component(bk, lc)
        add("B d0", 0, (), be, word, name)

    assert len(terms) == 9, len(terms)
    assert max(len(t.word) for t in terms) <= 2
    return terms


def generate_exact_terms() -> List[ExactTerm]:
    fresh.reset()
    terms: List[ExactTerm] = []
    tid = 0
    def add(source, order, deriv_indices, coeff, word, sig):
        nonlocal tid
        tid += 1
        terms.append(ExactTerm(f"T{tid:03d}", source, order, tuple(deriv_indices), coeff, tuple(word), sig))

    # Use fixed external indices for legibility; each block internally gets fresh dummy indices.
    a,b,c,d,e = "A","B","C","D","E"

    add("HH d4",4,(a,b,c,d), H(a,b)*H(c,d), (), "HH")
    add("H dH d3",3,(b,c,d), 2*H(a,b)*dH(c,d,a), (), "H dH")
    for ak in A_KINDS:
        lc=[0,0]; ae,w,n=A_component(ak,c,lc)
        add("H A d3",3,(a,b,c), 2*H(a,b)*ae,w,f"H {n}")
    add("H ddH d2",2,(c,d), H(a,b)*dH(c,d,a,b), (), "H ddH")
    for ak in A_KINDS:
        lc=[0,0]; ae,w,n=A_component(ak,e,lc)
        add("A dH d2",2,(c,d), ae*dH(c,d,e),w,f"{n} dH")
    for ak in A_KINDS:
        lc=[0,0]; ac,w,n=A_component(ak,c,lc)
        add("H dA d2",2,(b,c), 2*H(a,b)*ac.derivative(a),w,f"H d{n}")
    for ak1 in A_KINDS:
        for ak2 in A_KINDS:
            lc=[0,0]; ae,w1,n1=A_component(ak1,e,lc); ac,w2,n2=A_component(ak2,c,lc)
            add("A A d2",2,(e,c), ae*ac,w1+w2,f"{n1}{n2}")
    for bk in B_KINDS:
        lc=[0,0]; be,w,n=B_component(bk,lc)
        add("H B d2",2,(a,b), 2*H(a,b)*be,w,f"H {n}")
    for ak in A_KINDS:
        lc=[0,0]; ac,w,n=A_component(ak,c,lc)
        add("H ddA d1",1,(c,), H(a,b)*ac.second_derivative(a,b),w,f"H dd{n}")
    for ak1 in A_KINDS:
        for ak2 in A_KINDS:
            lc=[0,0]; ae,w1,n1=A_component(ak1,e,lc); ac,w2,n2=A_component(ak2,c,lc)
            add("A dA d1",1,(c,), ae*ac.derivative(e),w1+w2,f"{n1} d{n2}")
    for bk in B_KINDS:
        lc=[0,0]; be,w,n=B_component(bk,lc)
        add("H dB d1",1,(c,), 2*H(a,c)*be.derivative(a),w,f"H d{n}")
    for ak in A_KINDS:
        for bk in B_KINDS:
            lc=[0,0]; ac,w1,n1=A_component(ak,c,lc); be,w2,n2=B_component(bk,lc)
            add("A B d1",1,(c,), ac*be,w1+w2,f"{n1}{n2}")
    for bk in B_KINDS:
        for ak in A_KINDS:
            lc=[0,0]; be,w1,n1=B_component(bk,lc); ac,w2,n2=A_component(ak,c,lc)
            add("B A d1",1,(c,), be*ac,w1+w2,f"{n1}{n2}")
    for bk in B_KINDS:
        lc=[0,0]; be,w,n=B_component(bk,lc)
        add("H ddB d0",0,(), H(a,b)*be.second_derivative(a,b),w,f"H dd{n}")
    for ak in A_KINDS:
        for bk in B_KINDS:
            lc=[0,0]; ae,w1,n1=A_component(ak,e,lc); be,w2,n2=B_component(bk,lc)
            add("A dB d0",0,(), ae*be.derivative(e),w1+w2,f"{n1} d{n2}")
    for bk1 in B_KINDS:
        for bk2 in B_KINDS:
            lc=[0,0]; b1,w1,n1=B_component(bk1,lc); b2,w2,n2=B_component(bk2,lc)
            add("B B d0",0,(), b1*b2,w1+w2,f"{n1}{n2}")

    assert len(terms)==118, len(terms)
    assert max(len(t.word) for t in terms)<=4
    return terms

# Trace basis decomposition of an ordered generator word.
def trace_components(word: Tuple[Tuple[str,str], ...]) -> List[Tuple[str, str]]:
    L = [lab for sec,lab in word if sec=="L"]
    R = [lab for sec,lab in word if sec=="R"]
    nL,nR=len(L),len(R)
    if nL==0 and nR==0:
        return [("D","1")]
    # Any sector represented exactly once yields a vanishing trace factor.
    if nL==1 or nR==1:
        return [("ZERO","single-generator trace")]
    if nR==0:
        if nL==2: return [("L",f"t2L({L[0]},{L[1]})")]
        if nL==3: return [("L",f"t3L({','.join(L)})")]
        if nL==4:
            return [
                ("L",f"t4L({','.join(L)})"),
                ("LL",f"t2L({L[0]},{L[1]})*t2L({L[2]},{L[3]})"),
                ("LL",f"t2L({L[0]},{L[2]})*t2L({L[1]},{L[3]})"),
                ("LL",f"t2L({L[0]},{L[3]})*t2L({L[1]},{L[2]})"),
            ]
    if nL==0:
        if nR==2: return [("R",f"t2R({R[0]},{R[1]})")]
        if nR==3: return [("R",f"t3R({','.join(R)})")]
        if nR==4:
            return [
                ("R",f"t4R({','.join(R)})"),
                ("RR",f"t2R({R[0]},{R[1]})*t2R({R[2]},{R[3]})"),
                ("RR",f"t2R({R[0]},{R[2]})*t2R({R[1]},{R[3]})"),
                ("RR",f"t2R({R[0]},{R[3]})*t2R({R[1]},{R[2]})"),
            ]
    if nL==2 and nR==2:
        return [("LR",f"t2L({L[0]},{L[1]})*t2R({R[0]},{R[1]})")]
    return [("ZERO",f"factorized trace vanishes nL={nL},nR={nR}")]

FIELDS = [
    ("T",1,1,Fraction(1)),
    ("phi",0,0,Fraction(128)),
    ("BLL",2,0,Fraction(1,4)),
    ("BRR",0,2,Fraction(1,4)),
    ("UL",1,0,Fraction(-12)),
    ("UR",0,1,Fraction(-12)),
    ("ULLR",2,1,Fraction(-1,64)),
    ("ULRR",1,2,Fraction(-1,64)),
]
D_SPIN=16

FIELD_DETAILS = {
    "T": {
        "display": "T^alpha_baralpha",
        "latex": r"T^{\alpha}{}_{\bar\alpha}",
        "representation": r"S\otimes\bar S^{*}",
    },
    "phi": {
        "display": "phi",
        "latex": r"\phi",
        "representation": r"\mathbf 1",
    },
    "BLL": {
        "display": "B_LL^{alpha beta}",
        "latex": r"B_{LL}^{\alpha\beta}",
        "representation": r"S\otimes S",
    },
    "BRR": {
        "display": "B_RR_{baralpha barbeta}",
        "latex": r"B_{RR\,\bar\alpha\bar\beta}",
        "representation": r"\bar S^{*}\otimes\bar S^{*}",
    },
    "UL": {
        "display": "U_L^alpha",
        "latex": r"U_L^{\alpha}",
        "representation": r"S",
    },
    "UR": {
        "display": "U_R_baralpha",
        "latex": r"U_{R\,\bar\alpha}",
        "representation": r"\bar S^{*}",
    },
    "ULLR": {
        "display": "U_LLR^{alpha beta}_bargamma",
        "latex": r"U_{LLR}^{\alpha\beta}{}_{\bar\gamma}",
        "representation": r"S\otimes S\otimes\bar S^{*}",
    },
    "ULRR": {
        "display": "U_LRR^alpha_{barbeta bargamma}",
        "latex": r"U_{LRR}^{\alpha}{}_{\bar\beta\bar\gamma}",
        "representation": r"S\otimes\bar S^{*}\otimes\bar S^{*}",
    },
}

FIELD_REPRESENTATION_TEXT = {
    "T": "S x Sbar*",
    "phi": "scalar",
    "BLL": "S x S",
    "BRR": "Sbar* x Sbar*",
    "UL": "S",
    "UR": "Sbar*",
    "ULLR": "S x S x Sbar*",
    "ULRR": "S x Sbar* x Sbar*",
}

def moments(a:int,b:int,d:int=D_SPIN)->Dict[str,int]:
    return {
        "D": d**(a+b),
        "L": a*d**(a+b-1) if a else 0,
        "R": b*d**(a+b-1) if b else 0,
        "LL": a*(a-1)*d**(a+b-2) if a>=2 else 0,
        "RR": b*(b-1)*d**(a+b-2) if b>=2 else 0,
        "LR": a*b*d**(a+b-2) if a and b else 0,
        "ZERO": 0,
    }


def word_text(word):
    if not word: return "1"
    return " ".join(f"{s}[{l}]" for s,l in word)


def frac_text(x:Fraction)->str:
    return str(x.numerator) if x.denominator==1 else f"{x.numerator}/{x.denominator}"



def explicit_slot_trace_expansion(word: Tuple[Tuple[str,str], ...], a: int, b: int, d: int=D_SPIN):
    """Expand each total generator in the word into explicit tensor slots.

    Returns a dict trace_tensor -> integer coefficient after tracing each slot.
    The trace tensors retain the ordered generator labels inside each slot.
    """
    import itertools
    if any(sec=="L" for sec,_ in word) and a==0:
        return {"ZERO(no-L-slot)": 0}
    if any(sec=="R" for sec,_ in word) and b==0:
        return {"ZERO(no-R-slot)": 0}
    choices=[]
    for sec,_ in word:
        choices.append(range(1,a+1) if sec=="L" else range(1,b+1))
    assignments=[()] if not choices else itertools.product(*choices)
    out=defaultdict(int)
    for assn in assignments:
        Lslots={i:[] for i in range(1,a+1)}
        Rslots={j:[] for j in range(1,b+1)}
        for (sec,lab),slot in zip(word,assn):
            (Lslots if sec=="L" else Rslots)[slot].append(lab)
        factors=[]
        unused=0
        zero=False
        for slot in range(1,a+1):
            labs=Lslots[slot]
            if not labs: unused+=1
            elif len(labs)==1: zero=True; break
            else: factors.append(f"t{len(labs)}L({','.join(labs)})")
        if not zero:
            for slot in range(1,b+1):
                labs=Rslots[slot]
                if not labs: unused+=1
                elif len(labs)==1: zero=True; break
                else: factors.append(f"t{len(labs)}R({','.join(labs)})")
        if zero:
            tensor="ZERO(single-slot-single-generator)"
            coeff=0
        else:
            factors.sort()
            tensor="*".join(factors) if factors else "1"
            coeff=d**unused
        out[tensor]+=coeff
    return dict(out)


def _field_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def resolve_field(value: str):
    """Resolve a menu number or a forgiving ASCII field alias."""
    value = value.strip()
    if value.isdigit():
        index = int(value) - 1
        return FIELDS[index] if 0 <= index < len(FIELDS) else None
    aliases = {
        "t": "T",
        "phi": "phi",
        "scalar": "phi",
        "bll": "BLL",
        "brr": "BRR",
        "ul": "UL",
        "ur": "UR",
        "ullr": "ULLR",
        "ulrr": "ULRR",
    }
    key = aliases.get(_field_alias(value))
    return next((field for field in FIELDS if field[0] == key), None)


def latex_index(label: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)(\d+)", label)
    if match:
        stem, number = match.groups()
        if stem == "J":
            return rf"\bar J_{{{number}}}"
        return rf"{stem}_{{{number}}}"
    return label


def factor_latex(factor: Factor) -> str:
    idx = [latex_index(value) for value in factor.indices]
    kind = factor.kind
    if kind == "H":
        base = rf"\mathcal H^{{{idx[0]}{idx[1]}}}"
    elif kind == "GammaABC":
        base = rf"\Gamma_{{{idx[0]}{idx[1]}}}^{{\ {idx[2]}}}"
    elif kind == "GammaLUp":
        base = rf"\Gamma_{{L}}^{{{idx[0]},{idx[1]}}}"
    elif kind == "GammaRUp":
        base = rf"\Gamma_{{R}}^{{{idx[0]},{idx[1]}}}"
    elif kind == "GammaLDown":
        base = rf"\Gamma^{{L}}_{{{idx[0]},{idx[1]}}}"
    elif kind == "GammaRDown":
        base = rf"\Gamma^{{R}}_{{{idx[0]},{idx[1]}}}"
    elif kind == "Phi":
        base = rf"\Phi_{{{idx[0]}}}^{{{idx[1]}}}"
    elif kind == "BarPhi":
        base = rf"\bar\Phi_{{{idx[0]}}}^{{{idx[1]}}}"
    elif kind == "RicL":
        base = rf"\mathcal R_{{L}}^{{{idx[0]}}}"
    elif kind == "RicR":
        base = rf"\mathcal R_{{R}}^{{{idx[0]}}}"
    elif kind == "MixRL":
        base = rf"\mathcal R_{{RL}}^{{{idx[0]}{idx[1]}}}"
    elif kind == "MixLR":
        base = rf"\mathcal R_{{LR}}^{{{idx[0]}{idx[1]}}}"
    else:
        base = rf"\operatorname{{{kind}}}\!\left({','.join(idx)}\right)"
    derivatives = "".join(rf"\partial_{{{latex_index(value)}}}" for value in factor.derivs)
    return derivatives + base


def expr_latex(expr: Expr) -> str:
    if not expr.terms:
        return "0"
    rendered = []
    ordered = sorted(expr.terms.items(), key=lambda kv: tuple(x.text() for x in kv[0]))
    for monomial, coefficient in ordered:
        sign = -1 if coefficient < 0 else 1
        magnitude = abs(coefficient)
        factors = r"\,".join(factor_latex(factor) for factor in monomial)
        if magnitude == 1 and factors:
            body = factors
        else:
            scalar = frac_latex(magnitude)
            body = scalar if not factors else scalar + r"\," + factors
        rendered.append((sign, body))
    first_sign, first_body = rendered[0]
    output = ("-" if first_sign < 0 else "") + first_body
    for sign, body in rendered[1:]:
        output += (" - " if sign < 0 else " + ") + body
    return output


def expr_text(expr: Expr) -> str:
    if not expr.terms:
        return "0"
    rendered = []
    ordered = sorted(expr.terms.items(), key=lambda kv: tuple(x.text() for x in kv[0]))
    for monomial, coefficient in ordered:
        factors = " * ".join(factor.text() for factor in monomial) if monomial else "1"
        rendered.append(f"({frac_text(coefficient)}) * {factors}")
    return " + ".join(rendered).replace("+ (-", "- (")


def frac_latex(value: Fraction | int) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def derivative_latex(indices: Sequence[str]) -> str:
    return "".join(rf"\partial_{{{latex_index(value)}}}" for value in indices)


def word_latex(word: Tuple[Tuple[str, str], ...]) -> str:
    if not word:
        return r"\mathbf 1"
    return r"\,".join(
        rf"\mathcal G_{{{sector}}}^{{{latex_index(label)}}}" for sector, label in word
    )


def trace_tensor_latex(tensor: str) -> str:
    if tensor == "1":
        return "1"
    if tensor.startswith("ZERO") or tensor.startswith("factorized") or tensor == "single-generator trace":
        return "0"
    rendered = []
    for part in tensor.split("*"):
        match = re.fullmatch(r"t(\d+)([LR])\(([^)]*)\)", part)
        if not match:
            rendered.append(rf"\operatorname{{{part}}}")
            continue
        degree, sector, labels = match.groups()
        label_latex = ",".join(latex_index(value) for value in labels.split(","))
        rendered.append(rf"t_{{{degree}{sector}}}\!\left({label_latex}\right)")
    return r"\,".join(rendered)


def trace_terms(trace_order: int) -> List[ExactTerm]:
    if trace_order == 1:
        return generate_n1_terms()
    if trace_order == 2:
        return generate_exact_terms()
    raise ValueError(f"Unsupported trace order: {trace_order}")


def build_selected_trace(field, trace_order: int):
    name, a, b, weight = field
    moment_values = moments(a, b)
    terms = trace_terms(trace_order)
    rows = []
    for term in terms:
        for component_index, (basis, tensor) in enumerate(trace_components(term.word), 1):
            moment = moment_values[basis]
            rows.append({
                "field": name,
                "a": a,
                "b": b,
                "trace_order": trace_order,
                "n2_weight": frac_text(weight),
                "term_id": term.term_id,
                "component_index": component_index,
                "source": term.source,
                "derivative_order": term.derivative_order,
                "derivative_indices": " ".join(term.derivative_indices),
                "block_signature": term.block_signature,
                "word": word_text(term.word),
                "word_latex": word_latex(term.word),
                "trace_basis": basis,
                "trace_tensor": tensor,
                "trace_tensor_latex": trace_tensor_latex(tensor),
                "moment": moment,
                "weighted_n2_moment": frac_text(weight * moment) if trace_order == 2 else "not-applied",
                "coefficient_text": expr_text(term.coefficient),
                "coefficient_latex": expr_latex(term.coefficient),
                "external_derivative_latex": derivative_latex(term.derivative_indices),
            })
    return terms, rows, moment_values


def expanded_trace_contributions(terms: Sequence[ExactTerm], rows: Sequence[dict]):
    """Expand every nonzero selected-field contribution into primitive monomials."""
    by_id = {term.term_id: term for term in terms}
    expanded = []
    for row in rows:
        moment = row["moment"]
        if moment == 0:
            continue
        term = by_id[row["term_id"]]
        ordered_monomials = sorted(
            term.coefficient.terms.items(), key=lambda kv: tuple(factor.text() for factor in kv[0])
        )
        for primitive_index, (monomial, coefficient) in enumerate(ordered_monomials, 1):
            scalar = Fraction(moment) * coefficient
            formula_parts = [factor_latex(factor) for factor in monomial]
            if row["trace_tensor"] != "1":
                formula_parts.append(row["trace_tensor_latex"])
            formula_parts.extend(
                rf"\partial_{{{latex_index(index)}}}" for index in term.derivative_indices
            )
            formula_latex = r"\,\allowbreak\,".join(formula_parts) if formula_parts else "1"
            expanded.append({
                "term_id": term.term_id,
                "component_index": row["component_index"],
                "primitive_index": primitive_index,
                "source": term.source,
                "block_signature": term.block_signature,
                "trace_basis": row["trace_basis"],
                "trace_tensor": row["trace_tensor"],
                "moment": moment,
                "primitive_coeff_num": coefficient.numerator,
                "primitive_coeff_den": coefficient.denominator,
                "selected_scalar_num": scalar.numerator,
                "selected_scalar_den": scalar.denominator,
                "selected_scalar": frac_text(scalar),
                "formula_latex": formula_latex,
                "primitive_factors": " * ".join(factor.text() for factor in monomial) if monomial else "1",
                "external_derivative_indices": " ".join(term.derivative_indices),
            })
    return expanded


def tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def moment_result_latex(trace_order: int, moment_values: Dict[str, int]) -> str:
    bases = ["D", "L", "R"] if trace_order == 1 else ["D", "L", "R", "LL", "RR", "LR"]
    pieces = []
    for basis in bases:
        value = moment_values[basis]
        if value:
            symbol = rf"\mathfrak F_{{{basis}}}^{{({trace_order})}}"
            pieces.append(symbol if value == 1 else rf"{value}\,{symbol}")
    return " + ".join(pieces) if pieces else "0"


def operator_blocks_tex() -> str:
    return r"""
\begin{align*}
\Box_{a,b}
={}&\mathcal H^{AB}\partial_A\partial_B
+\left(h^C\mathbf 1+u^C_I\mathcal G_L^I+v^C_{\bar J}\mathcal G_R^{\bar J}\right)\partial_C\\
&+p_I\mathcal G_L^I+q_{\bar J}\mathcal G_R^{\bar J}
+r_{IK}\mathcal G_L^I\mathcal G_L^K
+s_{\bar J\bar L}\mathcal G_R^{\bar J}\mathcal G_R^{\bar L}
+t_{I\bar J}\mathcal G_L^I\mathcal G_R^{\bar J}.
\end{align*}
\begin{align*}
h^c={}&\mathcal H^{mn}\Gamma_{mn}{}^c,\\
u^c_I={}&\mathcal H^{cm}\Phi_{mI}-\Gamma_L^c{}_I,
&v^c_{\bar J}={}&\mathcal H^{cm}\bar\Phi_{m\bar J}+\Gamma_R^c{}_{\bar J},\\
p_I={}&\mathcal R_{L,I}+\frac12\mathcal H^{mn}\partial_m\Phi_{nI}
+\frac12\mathcal H^{mn}\Gamma_{mn}{}^c\Phi_{cI},\\
q_{\bar J}={}&-\mathcal R_{R,\bar J}+\frac12\mathcal H^{mn}\partial_m\bar\Phi_{n\bar J}
+\frac12\mathcal H^{mn}\Gamma_{mn}{}^c\bar\Phi_{c\bar J},\\
r_{IK}={}&\frac14\mathcal H^{mn}\Phi_{mI}\Phi_{nK}
-\frac12\Gamma_L^c{}_I\Phi_{cK}+\frac14\Gamma^L_{aI}\Gamma_L^a{}_K,\\
s_{\bar J\bar L}={}&\frac14\mathcal H^{mn}\bar\Phi_{m\bar J}\bar\Phi_{n\bar L}
+\frac12\Gamma_R^c{}_{\bar J}\bar\Phi_{c\bar L}
-\frac14\Gamma^R_{a\bar J}\Gamma_R^a{}_{\bar L},\\
t_{I\bar J}={}&\frac12\mathcal H^{mn}\Phi_{mI}\bar\Phi_{n\bar J}
-\frac12\Gamma_L^c{}_I\bar\Phi_{c\bar J}
+\frac12\Gamma_R^c{}_{\bar J}\Phi_{cI}
+\frac12\mathcal R_{RL,\bar J I}-\frac12\mathcal R_{LR,I\bar J}.
\end{align*}
"""


def n2_composition_tex() -> str:
    return r"""
\begin{align*}
\Box^2={}&
\mathcal H^{AB}\mathcal H^{CD}\partial_A\partial_B\partial_C\partial_D\\
&+2\mathcal H^{AB}(\partial_A\mathcal H^{CD})\partial_B\partial_C\partial_D
+2\mathcal H^{AB}\mathcal A^C\partial_A\partial_B\partial_C\\
&+\left[\mathcal H^{AB}(\partial_A\partial_B\mathcal H^{CD})
+\mathcal A^A(\partial_A\mathcal H^{CD})\right]\partial_C\partial_D\\
&+2\mathcal H^{AB}(\partial_A\mathcal A^C)\partial_B\partial_C
+\mathcal A^A\mathcal A^C\partial_A\partial_C
+2\mathcal H^{AB}\mathcal B\partial_A\partial_B\\
&+\left[\mathcal H^{AB}(\partial_A\partial_B\mathcal A^C)
+\mathcal A^A(\partial_A\mathcal A^C)
+2\mathcal H^{AC}(\partial_A\mathcal B)
+\mathcal A^C\mathcal B+\mathcal B\mathcal A^C\right]\partial_C\\
&+\mathcal H^{AB}(\partial_A\partial_B\mathcal B)
+\mathcal A^A(\partial_A\mathcal B)+\mathcal B^2.
\end{align*}
"""


def render_trace_tex(field, trace_order: int, terms, rows, expanded_rows, moment_values) -> str:
    name, a, b, weight = field
    details = FIELD_DETAILS[name]
    title_order = r"\operatorname{tr}_{\mathcal R_X}\Box_X" if trace_order == 1 else r"\operatorname{tr}_{\mathcal R_X}(\Box_X\circ\Box_X)"
    result_latex = moment_result_latex(trace_order, moment_values)
    nonzero_rows = sum(1 for row in rows if row["moment"] != 0)
    primitive_count = sum(term.coefficient.term_count() for term in terms)
    weighted_note = (
        rf"이 필드의 \(n=2\) 상쇄용 상대 가중치는 \(w_X={frac_latex(weight)}\)이다. "
        r"아래 boxed 결과는 가중치를 곱하지 않은 단일 필드 trace이다."
        if trace_order == 2
        else r"인수인계 자료의 \(w_X\propto M_X^{-4}\)는 \(n=2\) 전용이므로 이 \(n=1\) 결과에는 적용하지 않았다."
    )

    out = [r"""\documentclass[10pt,a4paper,landscape]{article}
\usepackage{fontspec}
\IfFontExistsTF{Malgun Gothic}{\setmainfont{Malgun Gothic}\setsansfont{Malgun Gothic}}{\setmainfont{Arial}\setsansfont{Arial}}
\IfFontExistsTF{Consolas}{\setmonofont{Consolas}}{\setmonofont{Courier New}}
\usepackage{amsmath,amssymb}
\usepackage{array,booktabs,longtable}
\usepackage[margin=13mm]{geometry}
\usepackage{xcolor}
\usepackage{hyperref}
\hypersetup{unicode=true,colorlinks=true,linkcolor=blue,urlcolor=blue}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\renewcommand{\arraystretch}{1.18}
\allowdisplaybreaks
\begin{document}
"""]
    out.append(rf"\begin{{center}}{{\LARGE 선택 필드 trace 계산}}\\[4pt]{{\large \({title_order}\)}}\end{{center}}")
    out.append(r"\section*{선택한 필드}")
    out.append(r"\begin{tabular}{@{}ll@{}}\toprule 항목 & 값\\\midrule")
    out.append(rf"필드 & \({details['latex']}\)\\")
    out.append(rf"raw 표현 & \(\mathcal R_X={details['representation']}\)\\")
    out.append(rf"tensor slot & \((a,b)=({a},{b})\), \(d=\dim S=\dim\bar S={D_SPIN}\)\\")
    out.append(rf"계산 & \(n={trace_order}\), \({title_order}\)\\")
    out.append(r"\bottomrule\end{tabular}")
    out.append("\n\n" + weighted_note + "\n")
    out.append(r"\begin{quote}\small 이 보고서는 raw tensor product, density weight 0, 공통 배경에서의 유한차원 spinor/tensor trace이다. 좌표 functional trace, determinant prefactor, 운동량 적분, regularization, irreducible projection은 포함하지 않는다.\end{quote}")
    out.append(r"대응하는 one-loop 항의 구조는 개략적으로")
    out.append(r"\[")
    out.append(rf"\Gamma_X^{{(n)}}\sim \frac{{\mu_Xc_X}}{{2nM_X^{{2n}}}}\operatorname{{Tr}}_x\!\left[\operatorname{{tr}}_{{\mathcal R_X}}\Box_X^n\right],\qquad n={trace_order},")
    out.append(r"\]")
    out.append(r"이며 이 보고서가 계산하는 부분은 대괄호 안의 유한차원 representation trace integrand이다.")

    out.append(r"\section*{연산자와 coefficient block}")
    out.append(operator_blocks_tex())
    if trace_order == 2:
        out.append(r"\subsection*{Ordered exact composition}")
        out.append(r"오른쪽 \(\Box\)가 먼저 작용하며 \(\mathcal A^C\mathcal B\)와 \(\mathcal B\mathcal A^C\)의 순서를 유지한다.")
        out.append(n2_composition_tex())

    out.append(r"\section*{선택 필드의 trace moment}")
    out.append(r"\[")
    out.append(rf"(D,L,R,LL,RR,LR)=({moment_values['D']},{moment_values['L']},{moment_values['R']},{moment_values['LL']},{moment_values['RR']},{moment_values['LR']}).")
    out.append(r"\]")
    if trace_order == 1:
        out.append(r"단일 generator trace와 좌우 sector에 하나씩만 있는 trace는 0이므로")
        out.append(r"""
\begin{align*}
\mathfrak F_D^{(1)}&=\mathcal H^{AB}\partial_A\partial_B+h^C\partial_C,\\
\mathfrak F_L^{(1)}&=r_{IK}\,t_{2L}(I,K),\\
\mathfrak F_R^{(1)}&=s_{\bar J\bar L}\,t_{2R}(\bar J,\bar L).
\end{align*}
""")
    else:
        out.append(r"118개 ordered block term을 trace basis별 universal functional로 묶어 \(\mathfrak F_{D,L,R,LL,RR,LR}^{(2)}\)로 표기한다.")
    out.append(r"\[")
    out.append(rf"\boxed{{{title_order}={result_latex}}}")
    out.append(r"\]")
    out.append(rf"전체 universal operator term은 {len(terms)}개, trace component는 {len(rows)}개이며 이 필드에서 moment가 0이 아닌 component는 {nonzero_rows}개이다. universal primitive coefficient monomial은 {primitive_count}개이고, 선택 필드의 0이 아닌 primitive 기여는 {len(expanded_rows)}개이다.")

    out.append(r"\section*{항별 trace 결과}")
    out.append(r"아래 표의 \(M\)이 선택 필드에서 해당 trace tensor에 곱해지는 정확한 정수 계수이다. coefficient의 primitive 완전 전개와 LaTeX 원문은 동봉 CSV에 기록한다.")
    out.append(r"\scriptsize")
    out.append(r"\begin{longtable}{@{}p{1.3cm}p{2.7cm}p{2.4cm}p{4.2cm}p{4.5cm}p{1.2cm}r@{}}")
    out.append(r"\toprule ID & source & block & generator word & trace tensor & basis & \(M\)\\\midrule\endfirsthead")
    out.append(r"\toprule ID & source & block & generator word & trace tensor & basis & \(M\)\\\midrule\endhead")
    out.append(r"\midrule\multicolumn{7}{r}{다음 페이지에 계속}\\\endfoot")
    out.append(r"\bottomrule\endlastfoot")
    for row in rows:
        out.append(
            f"{tex_escape(row['term_id'])} & "
            f"{tex_escape(row['source'])} & "
            f"{tex_escape(row['block_signature'])} & "
            rf"\({row['word_latex']}\) & "
            rf"\({row['trace_tensor_latex']}\) & "
            f"{tex_escape(row['trace_basis'])} & {row['moment']}\\\\"
        )
    out.append(r"\end{longtable}")
    out.append(r"\normalsize")

    out.append(r"\section*{선택 필드의 0이 아닌 primitive 기여식}")
    out.append(r"각 행은 선택 moment를 primitive coefficient에 곱한 실제 항이다. 마지막 열 전체가 LaTeX 수식으로 렌더링되며, 외부 \(\partial\)는 오른쪽 피계산 필드에 작용한다.")
    out.append(r"\scriptsize")
    out.append(r"\begin{longtable}{@{}p{1.25cm}p{0.8cm}p{2.4cm}p{2.2cm}p{1.6cm}>{\raggedright\arraybackslash}p{16.1cm}@{}}")
    out.append(r"\toprule ID & comp. & source & block & scalar & rendered primitive contribution\\\midrule\endfirsthead")
    out.append(r"\toprule ID & comp. & source & block & scalar & rendered primitive contribution\\\midrule\endhead")
    out.append(r"\midrule\multicolumn{6}{r}{다음 페이지에 계속}\\\endfoot")
    out.append(r"\bottomrule\endlastfoot")
    for row in expanded_rows:
        out.append(
            f"{tex_escape(row['term_id'])} & "
            f"{row['component_index']}.{row['primitive_index']} & "
            f"{tex_escape(row['source'])} & "
            f"{tex_escape(row['block_signature'])} & "
            rf"\({frac_latex(Fraction(row['selected_scalar_num'], row['selected_scalar_den']))}\) & "
            rf"\(\displaystyle {row['formula_latex']}\)\\"
        )
    out.append(r"\end{longtable}")
    out.append(r"\normalsize")
    out.append(r"\section*{해석 주의사항}")
    out.append(r"\begin{itemize}")
    out.append(r"\item \(n\)은 one-loop log-determinant에서 대응하는 operator power이지만, 여기서는 determinant prefactor와 functional trace를 제외한 representation trace만 계산한다. generator 개수와 같은 뜻이 아니다.")
    out.append(r"\item \(n=2\)에서는 \(\operatorname{tr}(\Box\circ\Box)\)를 계산하며 \((\operatorname{tr}\Box)^2\)로 바꾸지 않는다.")
    out.append(r"\item \(B_{LL},B_{RR},U_{LLR},U_{LRR}\)는 대칭화, 반대칭화 또는 gamma-traceless projection을 하지 않은 raw tensor product이다.")
    out.append(r"\item trace tensor \(t_{kL},t_{kR}\)는 선택한 gamma 정규화에 따른 metric contraction 이전의 추상 generator trace basis이다.")
    out.append(r"\end{itemize}")
    out.append(r"\end{document}")
    return "\n".join(out) + "\n"


def compile_trace_pdf(tex_path: Path) -> Path:
    engine = shutil.which("xelatex")
    if not engine:
        raise RuntimeError("xelatex를 찾을 수 없습니다. 생성된 .tex 파일을 LaTeX 환경에서 컴파일하세요.")
    command = [engine, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
    completed = subprocess.run(
        command,
        cwd=tex_path.parent,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=180,
    )
    pdf_path = tex_path.with_suffix(".pdf")
    if completed.returncode != 0 or not pdf_path.exists():
        tail = "\n".join((completed.stdout + "\n" + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"XeLaTeX 컴파일 실패:\n{tail}")
    for suffix in (".aux", ".log", ".out"):
        auxiliary = tex_path.with_suffix(suffix)
        if auxiliary.exists():
            auxiliary.unlink()
    return pdf_path


def write_selected_trace(field, trace_order: int, output_dir: Path, open_pdf: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    terms, rows, moment_values = build_selected_trace(field, trace_order)
    expanded_rows = expanded_trace_contributions(terms, rows)
    name = field[0]
    stem = f"trace_{name}_n{trace_order}"
    csv_path = output_dir / f"{stem}_details.csv"
    expanded_csv_path = output_dir / f"{stem}_expanded.csv"
    tex_path = output_dir / f"{stem}.tex"
    json_path = output_dir / f"{stem}_summary.json"

    csv_fields = list(rows[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(rows)

    expanded_csv_fields = list(expanded_rows[0].keys())
    with expanded_csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=expanded_csv_fields)
        writer.writeheader()
        writer.writerows(expanded_rows)

    tex_path.write_text(
        render_trace_tex(field, trace_order, terms, rows, expanded_rows, moment_values), encoding="utf-8"
    )
    pdf_path = compile_trace_pdf(tex_path)

    summary = {
        "field": name,
        "a": field[1],
        "b": field[2],
        "trace_order": trace_order,
        "spinor_dimension": D_SPIN,
        "moments": {key: moment_values[key] for key in ["D", "L", "R", "LL", "RR", "LR"]},
        "n2_relative_weight": frac_text(field[3]),
        "n2_weight_applied_to_boxed_result": False,
        "number_of_universal_operator_terms": len(terms),
        "number_of_trace_components": len(rows),
        "number_of_nonzero_components": sum(row["moment"] != 0 for row in rows),
        "number_of_primitive_monomials": sum(term.coefficient.term_count() for term in terms),
        "number_of_nonzero_expanded_contributions": len(expanded_rows),
        "finite_dimensional_trace": moment_result_latex(trace_order, moment_values),
        "scope": "raw tensor product, weight zero, finite-dimensional spinor/tensor trace before functional trace and regularization",
        "status": "GENERATED",
        "tex": str(tex_path),
        "pdf": str(pdf_path),
        "details_csv": str(csv_path),
        "expanded_csv": str(expanded_csv_path),
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if open_pdf and os.name == "nt":
        try:
            os.startfile(pdf_path)  # type: ignore[attr-defined]
        except OSError as exc:
            print(f"PDF 자동 열기에 실패했습니다. 직접 여세요: {pdf_path} ({exc})", file=sys.stderr)
    return summary


def run_full_verification(output_dir: str = OUTDIR):
    os.makedirs(output_dir, exist_ok=True)
    terms=generate_exact_terms()

    # Moment table and weighted cancellation.
    moment_rows=[]
    for name,a,b,w in FIELDS:
        m=moments(a,b)
        row={"field":name,"a":a,"b":b,"weight":frac_text(w),**m}
        moment_rows.append(row)
    sums={k:sum(w*moments(a,b)[k] for _,a,b,w in FIELDS) for k in ["D","L","R","LL","RR","LR"]}
    assert all(v==0 for v in sums.values()), sums

    with open(os.path.join(output_dir,"field_moments.csv"),"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=["field","a","b","weight","D","L","R","LL","RR","LR","ZERO"])
        writer.writeheader(); writer.writerows(moment_rows)
        writer.writerow({"field":"WEIGHTED_SUM","a":"","b":"","weight":"",**{k:frac_text(v) for k,v in sums.items()},"ZERO":0})

    # Universal 118 terms, fully expanded primitive background monomials.
    with open(os.path.join(output_dir,"universal_box2_118_terms.csv"),"w",newline="",encoding="utf-8") as f:
        fields=["term_id","source","derivative_order","derivative_indices","block_signature","word","primitive_monomial_index","coeff_num","coeff_den","primitive_factors"]
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for t in terms:
            for idx,(mon,c) in enumerate(sorted(t.coefficient.terms.items(), key=lambda kv: tuple(x.text() for x in kv[0])),1):
                writer.writerow({
                    "term_id":t.term_id,"source":t.source,"derivative_order":t.derivative_order,
                    "derivative_indices":" ".join(t.derivative_indices),"block_signature":t.block_signature,
                    "word":word_text(t.word),"primitive_monomial_index":idx,
                    "coeff_num":c.numerator,"coeff_den":c.denominator,
                    "primitive_factors":" * ".join(x.text() for x in mon) if mon else "1",
                })

    # 944 field-term operator substitutions and trace decompositions.
    with open(os.path.join(output_dir,"box2_terms_by_field.csv"),"w",newline="",encoding="utf-8") as f:
        fields=["field","a","b","weight","term_id","source","derivative_order","derivative_indices","block_signature","word","trace_basis","trace_tensor","unweighted_moment","weighted_moment"]
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for name,a,b,w in FIELDS:
            m=moments(a,b)
            for t in terms:
                for basis,tensor in trace_components(t.word):
                    val=m[basis]
                    writer.writerow({
                        "field":name,"a":a,"b":b,"weight":frac_text(w),"term_id":t.term_id,
                        "source":t.source,"derivative_order":t.derivative_order,
                        "derivative_indices":" ".join(t.derivative_indices),"block_signature":t.block_signature,
                        "word":word_text(t.word),"trace_basis":basis,"trace_tensor":tensor,
                        "unweighted_moment":val,"weighted_moment":frac_text(w*val),
                    })

    # Fully explicit slot-by-slot expansion for every field and every exact term.
    slot_rows=[]
    slot_aggregated=defaultdict(Fraction)
    for name,a,b,w in FIELDS:
        for t in terms:
            expansion=explicit_slot_trace_expansion(t.word,a,b)
            for tensor, coeff in sorted(expansion.items()):
                weighted=w*coeff
                slot_rows.append({
                    "field":name,"a":a,"b":b,"weight":frac_text(w),
                    "term_id":t.term_id,"source":t.source,"word":word_text(t.word),
                    "trace_tensor":tensor,"unweighted_coeff":coeff,
                    "weighted_coeff":frac_text(weighted),
                })
                slot_aggregated[(t.term_id,tensor)] += weighted
    with open(os.path.join(output_dir,"slot_expansion_by_field.csv"),"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(slot_rows[0].keys())); writer.writeheader(); writer.writerows(slot_rows)
    slot_verification=[]
    for (term_id,tensor),total in sorted(slot_aggregated.items()):
        assert total==0, (term_id,tensor,total)
        slot_verification.append({"term_id":term_id,"trace_tensor":tensor,"sum":frac_text(total),"status":"PASS"})
    with open(os.path.join(output_dir,"slot_coefficientwise_verification.csv"),"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(slot_verification[0].keys())); writer.writeheader(); writer.writerows(slot_verification)

    # Coefficientwise proof: every trace component of every one of the 118 exact terms sums to zero.
    verification=[]
    for t in terms:
        comps=trace_components(t.word)
        for comp_index,(basis,tensor) in enumerate(comps,1):
            contributions=[]
            total=Fraction(0)
            for name,a,b,w in FIELDS:
                val=moments(a,b)[basis]
                x=w*val
                contributions.append((name,x))
                total+=x
            if basis=="ZERO":
                assert total==0
            else:
                assert total==0, (t.term_id,basis,total)
            verification.append({
                "term_id":t.term_id,"component_index":comp_index,"source":t.source,
                "word":word_text(t.word),"trace_basis":basis,"trace_tensor":tensor,
                "contributions":"; ".join(f"{n}:{frac_text(x)}" for n,x in contributions),
                "sum":frac_text(total),"status":"PASS",
            })
    with open(os.path.join(output_dir,"coefficientwise_verification.csv"),"w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(verification[0].keys())); writer.writeheader(); writer.writerows(verification)

    primitive_rows=sum(t.coefficient.term_count() for t in terms)
    report={
        "number_of_exact_block_terms":len(terms),
        "number_of_fully_expanded_primitive_monomials":primitive_rows,
        "number_of_field_term_pairs":len(terms)*len(FIELDS),
        "number_of_trace_components_verified":len(verification),
        "number_of_explicit_slot_rows":len(slot_rows),
        "number_of_slot_trace_identities_verified":len(slot_verification),
        "weighted_moment_sums":{k:frac_text(v) for k,v in sums.items()},
        "max_generator_word_length":max(len(t.word) for t in terms),
        "status":"PASS",
        "scope":"raw tensor products, weight zero, common universal box/background/section/measure/regulator; finite-dimensional spinor supertrace coefficientwise before momentum integration",
    }
    with open(os.path.join(output_dir,"verification_summary.json"),"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)
    with open(os.path.join(output_dir,"verification_report.txt"),"w",encoding="utf-8") as f:
        for k,v in report.items():
            f.write(f"{k}: {v}\n")

    print(json.dumps(report,indent=2,ensure_ascii=False))
    return report


def print_field_menu():
    print("\n선택 가능한 필드 (raw tensor products)")
    print("-" * 96)
    print(f"{'번호':<6}{'필드':<38}{'(a,b)':<10}{'n=2 상대 가중치':<18}{'표현'}")
    print("-" * 96)
    for index, (name, a, b, weight) in enumerate(FIELDS, 1):
        details = FIELD_DETAILS[name]
        print(f"[{index}]   {details['display']:<36}({a},{b})     {frac_text(weight):<18}{FIELD_REPRESENTATION_TEXT[name]}")
    print("[q]   종료")


def prompt_for_field():
    while True:
        print_field_menu()
        try:
            choice = input("\n계산할 필드를 선택하세요: ").strip()
        except EOFError:
            return None
        if choice.lower() in {"q", "quit", "exit"}:
            return None
        field = resolve_field(choice)
        if field:
            return field
        print("올바른 번호 또는 필드 이름을 입력하세요.")


def prompt_for_trace_order():
    while True:
        print("\ntrace 계산을 선택하세요.")
        print("[1] n=1 : tr_R(Box)")
        print("[2] n=2 : tr_R(Box o Box), ordered exact composition")
        print("[b] 필드 선택으로 돌아가기")
        try:
            choice = input("\n계산 차수를 선택하세요: ").strip().lower()
        except EOFError:
            return None
        if choice in {"1", "n1", "n=1"}:
            return 1
        if choice in {"2", "n2", "n=2"}:
            return 2
        if choice in {"b", "back"}:
            return None
        print("1, 2 또는 b를 입력하세요.")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="필드를 선택하여 n=1 또는 n=2 finite-dimensional trace를 계산하고 LaTeX PDF로 렌더링합니다."
    )
    parser.add_argument("--field", help="필드 번호 또는 이름: T, phi, BLL, BRR, UL, UR, ULLR, ULRR")
    parser.add_argument("--trace-order", "--trace", type=int, choices=(1, 2), help="1=tr(Box), 2=tr(Box o Box)")
    parser.add_argument("--list-fields", action="store_true", help="필드 목록만 출력하고 종료")
    parser.add_argument("--verify-all", action="store_true", help="기존 전체 n=2 coefficientwise 검산을 실행")
    parser.add_argument("--output-dir", help="결과 저장 폴더")
    parser.add_argument("--no-open", action="store_true", help="생성된 PDF를 자동으로 열지 않음")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.list_fields:
        print_field_menu()
        return 0

    if args.verify_all:
        if args.field or args.trace_order:
            raise SystemExit("--verify-all은 --field/--trace-order와 함께 사용할 수 없습니다.")
        output_dir = args.output_dir or OUTDIR
        run_full_verification(output_dir)
        return 0

    if args.field:
        field = resolve_field(args.field)
        if not field:
            raise SystemExit(f"알 수 없는 필드: {args.field}")
    else:
        field = None

    trace_order = args.trace_order
    while field is None or trace_order is None:
        if field is None:
            field = prompt_for_field()
            if field is None:
                print("종료합니다.")
                return 0
        if trace_order is None:
            trace_order = prompt_for_trace_order()
            if trace_order is None:
                field = None

    output_dir = Path(args.output_dir) if args.output_dir else Path(OUTDIR) / "interactive_results"
    summary = write_selected_trace(field, trace_order, output_dir, open_pdf=not args.no_open)

    print("\n계산이 완료되었습니다.")
    print(f"필드: {summary['field']}  (a,b)=({summary['a']},{summary['b']})")
    print(f"n={trace_order}: operator terms={summary['number_of_universal_operator_terms']}, trace components={summary['number_of_trace_components']}")
    print("moments:", summary["moments"])
    print("LaTeX source:", summary["tex"])
    print("Rendered PDF:", summary["pdf"])
    print("Detailed CSV:", summary["details_csv"])
    print("Expanded contribution CSV:", summary["expanded_csv"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())
