import ast
from collections import Counter
from pathlib import Path
import threading
import unittest
from urllib.request import urlopen

import trace_selector_web as web


class TraceSelectorWebTests(unittest.TestCase):
    def test_python_310_grammar_compatibility(self):
        source = (Path(__file__).with_name("trace_selector_web.py")).read_text(encoding="utf-8")
        ast.parse(source, filename="trace_selector_web.py", feature_version=(3, 10))

    def test_home_renders_all_field_cards_with_mathjax(self):
        document = web.render_home()
        self.assertEqual(document.count('class="field-card"'), 8)
        self.assertIn("mathjax@3", document)
        self.assertIn("T^{\\alpha}", document)
        self.assertIn("U_{LLR}^{\\alpha\\beta}", document)
        self.assertNotIn(r"\mathcal R_X", document)
        self.assertNotIn("(a,b)", document)

    def test_order_and_result_pages(self):
        field = web.trace.resolve_field("ULLR")
        order_page = web.render_order(field)
        self.assertIn("trace 차수를 선택하세요", order_page)
        self.assertIn("field=ULLR&n=2", order_page)

        result_page = web.render_result(field, 2)
        self.assertIn("선택한 ULLR, n=2 전체 전개", result_page)
        self.assertIn('id="combined-expansion"', result_page)
        self.assertIn('data-notation-schema="main-2.1-2.6-E"', result_page)
        self.assertIn("ULLR, n=2 전체 404항 Einstein-contracted trace expansion", result_page)
        self.assertIn("pair-canonical slot-signature provenance 446항", result_page)
        self.assertIn("Einstein-contracted displayed 404 / 404항", result_page)
        self.assertIn("explicit local metric을 배경 텐서의 Einstein 수축으로 완전히 평가", result_page)
        self.assertIn(r"\mathfrak R_", result_page)
        self.assertNotIn(r"\eta^", result_page)
        self.assertNotIn(r"\bar\eta^", result_page)
        self.assertNotIn(r"\mathcal D", result_page.split("<main>", 1)[1])
        self.assertNotIn(r"\mathcal R_X", order_page)
        self.assertNotIn(r"w_X", order_page)

    def test_standard_results_hide_internal_notation_for_all_fields_and_orders(self):
        forbidden = [
            r"\mathfrak F", r"t_{2L}", r"t_{2R}", r"t_{3L}", r"t_{3R}",
            r"t_{4L}", r"t_{4R}", r"\mathcal G_L", r"\mathcal G_R",
            r"\Gamma_{L}", r"\Gamma_{R}", r"\mathcal R_{L}", r"\mathcal R_{R}",
            r"I_{1}", r"\bar J", r"\mathcal D", "Trace decomposition", "Primitive expansion",
        ]
        for field in web.trace.FIELDS:
            for order in (1, 2):
                document = web.render_result(field, order)
                visible_main = document.split("<main>", 1)[1].split("</main>", 1)[0]
                for token in forbidden:
                    self.assertNotIn(token, visible_main, (field[0], order, token))
                if order == 2:
                    self.assertNotIn(r"\gamma^{", visible_main, field[0])
                    self.assertNotIn(r"\bar\gamma^{", visible_main, field[0])
                    self.assertNotIn(r"\eta^{", visible_main, field[0])
                    self.assertNotIn(r"\bar\eta^{", visible_main, field[0])
                    self.assertNotIn(r"G^{", visible_main, field[0])
                    self.assertNotIn(r"\bar G^{", visible_main, field[0])

    def test_n1_uses_fully_evaluated_main_pdf_notation(self):
        field = web.trace.resolve_field("T")
        equation = web.main_n1_trace_latex(field)
        self.assertIn("256", equation)
        self.assertIn(r"\mathcal H^{AB}\partial_A\partial_B", equation)
        self.assertIn(r"{}-\frac{1}{8}\,\mathcal H^{AB}\Phi_{A pq}\Phi_B{}^{pq}", equation)
        self.assertIn(r"{}-\frac{1}{4}\,\Gamma^{C}{}_{\bar p\bar q}\bar\Phi_C{}^{\bar p\bar q}", equation)
        self.assertNotIn(r"t_{", equation)

    def test_n2_preserves_main_pdf_order_and_barred_generator_sign(self):
        field = web.trace.resolve_field("T")
        equation = web.main_n2_trace_latex(field)
        self.assertIn(
            r"\Delta\circ\Delta-\Delta\circ\bar\Delta-\bar\Delta\circ\Delta+\bar\Delta\circ\bar\Delta",
            equation,
        )
        action = web.main_generator_action_latex(field)
        self.assertIn(r"G^{q_1q_2}T^{\alpha}_{\bar\alpha}=\frac12", action)
        self.assertIn(r"\bar G^{\bar q_1\bar q_2}T^{\alpha}_{\bar\alpha}=-\frac12", action)
        barred_delta = web.main_delta_latex(barred=True)
        self.assertIn(r"\bar G^{\bar q_1\bar q_2}\bar G^{\bar q_3\bar q_4}T", barred_delta)
        self.assertIn(r"G^{q_1q_2}\bar G^{\bar q_3\bar q_4}T", barred_delta)

    def test_raw_slot_trace_normalization_and_order(self):
        left_two = web.main_slot_trace_expansion(
            (("L", "I1"), ("L", "I2")), 2, 0
        )
        self.assertEqual(left_two, [(8, (("I1", "I2"),), ())])

        right_two = web.main_slot_trace_expansion(
            (("R", "J1"), ("R", "J2")), 0, 2
        )
        self.assertEqual(right_two, [(8, (), (("J2", "J1"),))])

        right_three = web.main_slot_trace_expansion(
            (("R", "J1"), ("R", "J2"), ("R", "J3")), 0, 1
        )
        self.assertEqual(right_three, [(-web.Fraction(1, 8), (), (("J3", "J2", "J1"),))])
        self.assertEqual(web.main_slot_trace_expansion((("L", "I1"),), 2, 0), [])

        left_four = web.main_slot_trace_expansion(
            (("L", "I1"), ("L", "I2"), ("L", "I3"), ("L", "I4")), 2, 0
        )
        self.assertEqual(len(left_four), 4)
        self.assertIn((2, (("I1", "I2", "I3", "I4"),), ()), left_four)
        self.assertEqual(sum(coefficient == web.Fraction(1, 8) for coefficient, _left, _right in left_four), 3)

        mixed_two_two = (("L", "I1"), ("L", "I2"), ("R", "J1"), ("R", "J2"))
        self.assertEqual(
            web.main_slot_trace_expansion(mixed_two_two, 2, 1),
            [(2, (("I1", "I2"),), (("J2", "J1"),))],
        )
        self.assertEqual(
            web.main_slot_trace_expansion(mixed_two_two, 1, 2),
            [(2, (("I1", "I2"),), (("J2", "J1"),))],
        )

    def test_raw_slot_engine_reproduces_t_and_phi_goldens(self):
        self.assertEqual(
            web.main_raw_field_n2_primitive_terms(web.trace.resolve_field("T")),
            web.main_t_n2_primitive_terms(),
        )
        self.assertEqual(
            web.main_raw_field_n2_primitive_terms(web.trace.resolve_field("phi")),
            web.main_phi_n2_primitive_terms(),
        )

    def test_bare_chiral_bivector_traces_have_2_8_60_terms(self):
        expected = {
            2: (2, Counter({-16: 1, 16: 1})),
            3: (8, Counter({-16: 4, 16: 4})),
            4: (60, Counter({-16: 30, 16: 30})),
        }
        for length, (count, coefficients) in expected.items():
            labels = tuple(f"I{index}" for index in range(1, length + 1))
            terms = web.main_bivector_trace_eta_terms(labels, "L")
            self.assertEqual(len(terms), count)
            self.assertEqual(Counter(coefficient for coefficient, _body in terms), coefficients)
        self.assertEqual(
            web.main_bivector_trace_eta_terms(("I1", "I2"), "L"),
            (
                (-16, (("L", 1, 3), ("L", 2, 4))),
                (16, (("L", 1, 4), ("L", 2, 3))),
            ),
        )

    def test_bare_trace_reversal_and_component_goldens(self):
        for length in (2, 3, 4):
            labels = tuple(f"J{index}" for index in range(1, length + 1))
            forward = {
                monomial: coefficient
                for coefficient, monomial in web.main_bivector_trace_eta_terms(labels, "R")
            }
            reversed_trace = {
                monomial: coefficient
                for coefficient, monomial in web.main_bivector_trace_eta_terms(
                    tuple(reversed(labels)), "R"
                )
            }
            self.assertEqual(
                reversed_trace,
                {monomial: (-1) ** length * coefficient for monomial, coefficient in forward.items()},
            )

        def euclidean_component(length, assignment):
            labels = tuple(f"I{index}" for index in range(1, length + 1))
            return sum(
                coefficient
                for coefficient, monomial in web.main_bivector_trace_eta_terms(labels, "L")
                if all(assignment[first] == assignment[second] for _sector, first, second in monomial)
            )

        self.assertEqual(euclidean_component(2, {1: 1, 2: 2, 3: 1, 4: 2}), -16)
        self.assertEqual(
            euclidean_component(3, {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 1}),
            16,
        )
        self.assertEqual(
            euclidean_component(
                4, {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 1}
            ),
            16,
        )

    def test_ur_three_generator_sign_cancels_barred_reversal(self):
        left_word = (("L", "I1"), ("L", "I2"), ("L", "I3"))
        right_word = (("R", "J1"), ("R", "J2"), ("R", "J3"))
        left_scale, left_words, _empty_right = web.main_slot_trace_expansion(
            left_word, 1, 0
        )[0]
        right_scale, _empty_left, right_words = web.main_slot_trace_expansion(
            right_word, 0, 1
        )[0]
        left = {
            tuple((first, second) for _sector, first, second in monomial): left_scale * coefficient
            for coefficient, monomial in web.main_slot_raw_eta_expansion(left_words, ())
        }
        right = {
            tuple((first, second) for _sector, first, second in monomial): right_scale * coefficient
            for coefficient, monomial in web.main_slot_raw_eta_expansion((), right_words)
        }
        self.assertEqual(left_scale, web.Fraction(1, 8))
        self.assertEqual(right_scale, web.Fraction(-1, 8))
        self.assertEqual(right, left)

    def test_background_contracted_pair_flip_goldens(self):
        expected = {
            2: [-32],
            3: [128],
            4: [64, -256, 256, 64, -256, 64],
        }
        for length, coefficients in expected.items():
            selected = next(
                term
                for term in web.trace.generate_exact_terms()
                if len(term.word) == length and all(sector == "L" for sector, _label in term.word)
            )
            monomial = next(iter(selected.coefficient.terms))
            left_words = (tuple(label for _sector, label in selected.word),)
            terms = web.main_slot_eta_expansion(
                left_words, (), selected.word, monomial
            )
            self.assertEqual([coefficient for coefficient, _body in terms], coefficients)

    def test_pair_flip_validation_fails_closed(self):
        word = (("L", "I1"),)
        with self.assertRaises(ValueError):
            web._main_validate_pair_flip_monomial((), word)
        bad_slot = (web.trace.Factor("H", ("I1", "B")),)
        with self.assertRaises(ValueError):
            web._main_validate_pair_flip_monomial(bad_slot, word)
        duplicate = (
            web.trace.Factor("Phi", ("A", "I1")),
            web.trace.Factor("Phi", ("B", "I1")),
        )
        with self.assertRaises(ValueError):
            web._main_validate_pair_flip_monomial(duplicate, word)

    def test_eta_absorption_matches_the_two_bivector_golden(self):
        monomial = tuple(sorted((
            web.trace.Factor("GammaLUp", ("C", "I2")),
            web.trace.Factor("GammaLUp", ("E", "I1")),
        )))
        word = (("L", "I1"), ("L", "I2"))
        eta_monomial = (("L", 1, 3), ("L", 2, 4))
        key, assignment = web.main_absorb_eta_contraction(
            monomial, word, eta_monomial
        )
        self.assertEqual(key, assignment)
        body = web.main_contracted_body_latex(
            monomial, web.main_coordinate_map(monomial), assignment, ()
        )
        self.assertEqual(body, r"\Gamma^{Cpq}\,\Gamma^{E}{}_{pq}")
        self.assertNotIn(r"\eta", body)

    def test_eta_absorption_supports_triangle_mixed_variance(self):
        monomial = tuple(sorted((
            web.trace.Factor("Phi", ("A", "I1")),
            web.trace.Factor("Phi", ("B", "I2")),
            web.trace.Factor("Phi", ("C", "I3")),
        )))
        word = (("L", "I1"), ("L", "I2"), ("L", "I3"))
        eta_monomial = (("L", 1, 3), ("L", 2, 5), ("L", 4, 6))
        _key, assignment = web.main_absorb_eta_contraction(
            monomial, word, eta_monomial
        )
        body = web.main_contracted_body_latex(
            monomial, web.main_coordinate_map(monomial), assignment, ()
        )
        self.assertIn(r"\Phi_{Apq}", body)
        self.assertIn(r"\Phi_{B}{}^{p}{}_{r}", body)
        self.assertIn(r"\Phi_{C}{}^{qr}", body)
        self.assertNotIn(r"\eta", body)

    def test_eta_absorption_and_mixed_ricci_fail_closed_and_render_unambiguously(self):
        monomial = (
            web.trace.Factor("RicL", ("I1",)),
            web.trace.Factor("RicL", ("I2",)),
        )
        word = (("L", "I1"), ("L", "I2"))
        with self.assertRaises(ValueError):
            web.main_absorb_eta_contraction(
                monomial,
                word,
                (("L", 1, 2), ("L", 3, 4)),
            )
        with self.assertRaises(ValueError):
            web.main_absorb_eta_contraction(
                monomial,
                word,
                (("L", 1, 3), ("L", 1, 4)),
            )

        factor = web.trace.Factor("RicL", ("I1",))
        down_up = (("I1", (("L", 0, "down"), ("L", 1, "up"))),)
        up_down = (("I1", (("L", 0, "up"), ("L", 1, "down"))),)
        self.assertEqual(
            web.main_contracted_factor_latex(factor, {}, down_up),
            r"\mathfrak R_{p}{}^{q}",
        )
        self.assertEqual(
            web.main_contracted_factor_latex(factor, {}, up_down),
            r"\mathfrak R^{p}{}_{q}",
        )
        self.assertNotIn(
            "[",
            web.main_contracted_factor_latex(factor, {}, down_up),
        )

    def test_raw_slot_coefficients_match_the_independent_slot_audit(self):
        for field in web.trace.FIELDS:
            name, a, b, _weight = field
            for term in web.trace.generate_exact_terms():
                expected = {
                    tensor: coefficient
                    for tensor, coefficient in web.trace.explicit_slot_trace_expansion(
                        term.word, a, b
                    ).items()
                    if coefficient
                }
                actual = {}
                right_count = sum(sector == "R" for sector, _label in term.word)
                undo_generator_normalization = web.Fraction(
                    2 ** len(term.word), (-1) ** right_count
                )
                for coefficient, left_words, right_words in web.main_slot_trace_expansion(
                    term.word, a, b
                ):
                    factors = [
                        f"t{len(labels)}L({','.join(labels)})"
                        for labels in left_words
                    ]
                    factors.extend(
                        f"t{len(labels)}R({','.join(reversed(labels))})"
                        for labels in right_words
                    )
                    tensor = "*".join(sorted(factors)) if factors else "1"
                    unscaled = coefficient * undo_generator_normalization
                    self.assertEqual(unscaled.denominator, 1, (name, term.term_id))
                    actual[tensor] = unscaled.numerator
                self.assertEqual(actual, expected, (name, term.term_id))

    def test_all_six_raw_tensor_fields_have_complete_d_free_ledgers(self):
        expected = {
            "BLL": (192, 222, 27, 30, Counter({4: 1, 3: 2, 2: 12, 1: 46, 0: 131})),
            "BRR": (192, 222, 27, 30, Counter({4: 1, 3: 2, 2: 12, 1: 46, 0: 131})),
            "UL": (192, 195, 27, 27, Counter({4: 1, 3: 2, 2: 12, 1: 46, 0: 131})),
            "UR": (192, 195, 27, 27, Counter({4: 1, 3: 2, 2: 12, 1: 46, 0: 131})),
            "ULLR": (404, 446, 48, 51, Counter({4: 1, 3: 2, 2: 19, 1: 86, 0: 296})),
            "ULRR": (404, 446, 48, 51, Counter({4: 1, 3: 2, 2: 19, 1: 86, 0: 296})),
        }
        forbidden = (
            r"\mathcal D", r"G^", r"\bar G", r"I_", r"\bar J",
            r"t_{2L}", r"t_{2R}", r"\mathcal G_L", r"\mathcal G_R",
        )
        for name, (count, provenance_count, nonzero_blocks, signatures, derivative_counts) in expected.items():
            field = web.trace.resolve_field(name)
            terms = web.main_raw_field_n2_primitive_terms(field)
            provenance = web.main_raw_field_n2_provenance_terms(field)
            self.assertEqual(len(terms), count, name)
            self.assertEqual(len(provenance), provenance_count, name)
            self.assertEqual(Counter(order for order, _coefficient, _body in terms), derivative_counts, name)

            equation = web.main_raw_field_n2_full_trace_latex(field)
            self.assertEqual(equation.count(r"\\[0.65em]"), count - 1, name)
            for token in forbidden:
                self.assertNotIn(token, equation, (name, token))
            self.assertNotIn(r"\gamma", equation, name)
            self.assertNotIn(r"\bar\gamma", equation, name)
            self.assertNotIn(r"\eta", equation, name)
            self.assertNotIn(r"\bar\eta", equation, name)

            document = web.render_result(field, 2)
            visible_main = document.split("<main>", 1)[1].split("</main>", 1)[0]
            chunks = web.main_n2_trace_latex_chunks(field, terms)
            self.assertEqual(sum(chunk[3] for chunk in chunks), count, name)
            self.assertEqual(
                visible_main.count('class="lazy-math formula-part"'), len(chunks), name
            )
            self.assertLess(
                max(len(chunk[4].encode("utf-8")) for chunk in chunks),
                1024 * 1024,
                name,
            )
            self.assertIn(web.esc(r"\displaystyle " + chunks[-1][4]), visible_main, name)
            self.assertIn(f"pair-canonical slot-signature provenance {provenance_count}항", visible_main, name)
            self.assertIn(f"Einstein-contracted displayed {count} / {count}항", visible_main, name)
            self.assertIn(
                f"trace 후보 block {nonzero_blocks}개 + 확정 0 block {118 - nonzero_blocks}개",
                visible_main,
                name,
            )
            self.assertIn(f"raw-slot signature {signatures}개", visible_main, name)
            self.assertIn('class="combined-formula formula-stack"', visible_main, name)
            self.assertIn('class="lazy-math formula-part"', visible_main, name)
            self.assertNotIn("64 / 64 ordered terms", visible_main, name)
            self.assertNotIn(r"\mathcal D", visible_main, name)

    def test_n2_full_expansion_is_lazy_mathjax_content(self):
        field = web.trace.resolve_field("T")
        terms = web.main_t_n2_primitive_terms()
        chunks = web.main_n2_trace_latex_chunks(field, terms)
        self.assertEqual(sum(chunk[3] for chunk in chunks), len(terms))
        self.assertTrue(all(chunk[3] <= web.TRACE_TERMS_PER_MATH_NODE for chunk in chunks))
        self.assertLess(max(len(chunk[4].encode("utf-8")) for chunk in chunks), 1024 * 1024)
        self.assertTrue(any(part_count > 1 for _order, _part, part_count, _count, _latex in chunks))

        document = web.render_result(field, 2)
        self.assertIn('class="combined-formula formula-stack"', document)
        self.assertEqual(document.count('class="lazy-math formula-part"'), len(chunks))
        self.assertIn('aria-busy="true"', document)
        self.assertIn('tabindex="0"', document)
        self.assertIn('data-derivative-order="0"', document)
        self.assertIn("IntersectionObserver", document)
        self.assertIn("tex2svgPromise", document)

    def test_t_n2_evaluates_329_candidates_to_404_einstein_terms(self):
        symbolic_terms = web.main_t_n2_symbolic_gamma_terms()
        self.assertEqual(len(symbolic_terms), 329)
        barred_two = next(
            body for _order, _coefficient, body in symbolic_terms
            if body.count(r"\bar\gamma") >= 2
        )
        self.assertIn(
            r"\bar\gamma^{\bar q_3\bar q_4}\,\bar\gamma^{\bar q_1\bar q_2}",
            barred_two,
        )

        terms = web.main_t_n2_primitive_terms()
        self.assertEqual(len(terms), 404)
        self.assertEqual(
            Counter(order for order, _coefficient, _body in terms),
            Counter({4: 1, 3: 2, 2: 19, 1: 86, 0: 296}),
        )
        self.assertEqual(terms[0][1], 256)
        self.assertIn(r"\mathcal H^{AB}\,\mathcal H^{CD}", terms[0][2])
        self.assertFalse(any(r"\eta^" in body for _order, _coefficient, body in terms))
        self.assertTrue(any(r"{}^{" in body for _order, _coefficient, body in terms))
        equation = web.main_t_n2_full_trace_latex()
        self.assertEqual(equation.count(r"\\[0.65em]"), 403)
        for token in (
            r"\mathcal G_L", r"\mathcal G_R", r"\Gamma_L", r"\Gamma_R",
            r"\mathcal R_L", r"\mathcal R_R", r"I_1", r"\bar J", r"t_{2L}",
            r"\gamma", r"\bar\gamma", r"\eta", r"\bar\eta",
        ):
            self.assertNotIn(token, equation)

        document = web.render_result(web.trace.resolve_field("T"), 2)
        self.assertIn("trace 후보 block 48개 + 확정 0 block 70개", document)
        self.assertIn("Clifford trace 전 candidate 329개", document)
        self.assertIn("pair-canonical slot-signature provenance 419항", document)
        self.assertIn("Einstein-contracted displayed 404 / 404항", document)
        self.assertIn("그 밖의 tensor identity나 contraction-graph orientation 동치는 사용하지 않았습니다", document)
        self.assertIn("외부 미분차수 4→0: 1, 2, 19, 86, 296", document)
        visible_main = document.split("<main>", 1)[1].split("</main>", 1)[0]
        self.assertNotIn(r"\mathcal D", visible_main)
        self.assertNotIn(r"\gamma^{", visible_main)
        self.assertNotIn(r"\bar\gamma^{", visible_main)
        self.assertNotIn("main.pdf equations (2.1), (2.2)", visible_main)

    def test_phi_n2_fully_expands_covariant_derivatives(self):
        terms = web.main_phi_n2_primitive_terms()
        self.assertEqual(len(terms), 14)
        self.assertEqual(
            Counter(order for order, _coefficient, _body in terms),
            Counter({4: 1, 3: 2, 2: 5, 1: 6}),
        )
        self.assertEqual(terms[0][1], 1)
        self.assertIn(r"\mathcal H^{AB}\,\mathcal H^{CD}", terms[0][2])

        equation = web.main_phi_n2_full_trace_latex()
        self.assertEqual(equation.count(r"\\[0.65em]"), 13)
        self.assertIn(
            r"\partial_{A}\,\partial_{B}\,\partial_{C}\,\partial_{D}",
            equation,
        )
        self.assertIn(r"\partial_{A}\partial_{B}\Gamma_", equation)
        for token in (r"\mathcal D", r"G^", r"\bar G", r"\circ\Bigl"):
            self.assertNotIn(token, equation)

        document = web.render_result(web.trace.resolve_field("phi"), 2)
        visible_main = document.split("<main>", 1)[1].split("</main>", 1)[0]
        self.assertIn("ordinary-partial 14 / 14항", visible_main)
        self.assertIn("외부 미분차수 4→0: 1, 2, 5, 6, 0", visible_main)
        self.assertIn("1차원 index trace를 완전히 평가", visible_main)
        self.assertNotIn(r"\mathcal D", visible_main)
        self.assertNotIn("64 / 64 ordered terms", visible_main)

    def test_scalar_box_specialization_has_only_ordinary_derivatives(self):
        equation = web.main_phi_box_latex()
        self.assertEqual(
            equation,
            r"\left.\Box\right|_{\mathbf 1}=\mathcal H^{AB}\partial_A\partial_B"
            r"+\mathcal H^{AB}\Gamma_{AB}{}^{C}\partial_C",
        )
        self.assertNotIn(r"\mathcal D", equation)

    def test_generator_action_uses_the_selected_field_symbol(self):
        bll_action = web.main_generator_action_latex(web.trace.resolve_field("BLL"))
        self.assertIn(r"G^{q_1q_2}B_{LL}^{\alpha_1\cdots\alpha_2}", bll_action)
        self.assertNotIn(r"G^{q_1q_2}T", bll_action)

        phi_action = web.main_generator_action_latex(web.trace.resolve_field("phi"))
        self.assertIn(r"G^{q_1q_2}\phi=0", phi_action)
        self.assertIn(r"\bar G^{\bar q_1\bar q_2}\phi=0", phi_action)

        for name in ("UR", "BRR", "ULLR", "ULRR"):
            action = web.main_generator_action_latex(web.trace.resolve_field(name))
            self.assertIn(r"{}_{\bar", action, name)
            self.assertNotIn(web.FIELD_OPERATOR_LATEX[name] + r"_{\bar", action, name)

    def test_combined_equation_normalizes_signs_and_unit_coefficients(self):
        field = web.trace.resolve_field("T")
        rows = [
            {"selected_scalar_num": 1, "selected_scalar_den": 1, "formula_latex": "A"},
            {"selected_scalar_num": -1, "selected_scalar_den": 1, "formula_latex": "B"},
            {"selected_scalar_num": 1, "selected_scalar_den": 2, "formula_latex": "C"},
        ]
        equation = web.combined_expansion_latex(field, 1, rows)
        self.assertTrue(equation.startswith(r"\begin{aligned}"))
        self.assertIn(r"&=A\quad {}-B", equation)
        self.assertIn(r"{}+\frac{1}{2}\,C", equation)
        self.assertNotIn("+-", equation)
        self.assertNotIn("-1\\,B", equation)

    def test_combined_equation_removes_pdf_only_allowbreak(self):
        field = web.trace.resolve_field("phi")
        rows = [{
            "selected_scalar_num": 1,
            "selected_scalar_den": 1,
            "formula_latex": r"A\,\allowbreak\,B",
        }]
        equation = web.combined_expansion_latex(field, 1, rows)
        self.assertNotIn(r"\allowbreak", equation)
        self.assertIn(r"A\,\,B", equation)

    def test_http_health_and_home(self):
        server = web.TraceHTTPServer((web.HOST, 0), web.TraceHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://{web.HOST}:{server.server_address[1]}"
            with urlopen(base + "/health", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'"fields": 8', response.read())
            with urlopen(base + "/", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("계산할 필드를 선택하세요", response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
