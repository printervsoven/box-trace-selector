import unittest

import verify_direct_box2 as verifier


class TraceSelectorTests(unittest.TestCase):
    def test_field_moments(self):
        expected = {
            "T": (256, 16, 16, 0, 0, 1),
            "phi": (1, 0, 0, 0, 0, 0),
            "BLL": (256, 32, 0, 2, 0, 0),
            "BRR": (256, 0, 32, 0, 2, 0),
            "UL": (16, 1, 0, 0, 0, 0),
            "UR": (16, 0, 1, 0, 0, 0),
            "ULLR": (4096, 512, 256, 32, 0, 32),
            "ULRR": (4096, 256, 512, 0, 32, 32),
        }
        for name, a, b, _ in verifier.FIELDS:
            values = verifier.moments(a, b)
            actual = tuple(values[key] for key in ("D", "L", "R", "LL", "RR", "LR"))
            self.assertEqual(actual, expected[name])

    def test_n1_term_inventory_and_trace(self):
        terms = verifier.generate_n1_terms()
        self.assertEqual(len(terms), 9)
        self.assertEqual(sum(term.coefficient.term_count() for term in terms), 23)
        field = verifier.resolve_field("T")
        terms, rows, _ = verifier.build_selected_trace(field, 1)
        self.assertEqual(len(rows), 9)
        self.assertEqual(sum(row["moment"] != 0 for row in rows), 4)
        expanded = verifier.expanded_trace_contributions(terms, rows)
        self.assertEqual(len(expanded), 8)
        self.assertTrue(all(row["formula_latex"] for row in expanded))

    def test_n2_inventory_is_unchanged(self):
        terms = verifier.generate_exact_terms()
        self.assertEqual(len(terms), 118)
        self.assertEqual(sum(term.coefficient.term_count() for term in terms), 867)
        self.assertEqual(sum(len(verifier.trace_components(term.word)) for term in terms), 124)
        _, rows, _ = verifier.build_selected_trace(verifier.resolve_field("ULLR"), 2)
        self.assertEqual(len(verifier.expanded_trace_contributions(terms, rows)), 356)

    def test_dummy_indices_are_deterministic(self):
        first = [term.coefficient.serialize() for term in verifier.generate_n1_terms()]
        verifier.generate_exact_terms()
        second = [term.coefficient.serialize() for term in verifier.generate_n1_terms()]
        self.assertEqual(first, second)

    def test_field_aliases(self):
        self.assertEqual(verifier.resolve_field("1")[0], "T")
        self.assertEqual(verifier.resolve_field("B_LL")[0], "BLL")
        self.assertEqual(verifier.resolve_field("u-lrr")[0], "ULRR")
        self.assertIsNone(verifier.resolve_field("unknown"))


if __name__ == "__main__":
    unittest.main()
