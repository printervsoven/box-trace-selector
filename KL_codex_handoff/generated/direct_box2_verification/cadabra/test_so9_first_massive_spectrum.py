"""Acceptance tests for the actual first-massive Type-II Spin(9) spectrum."""

from fractions import Fraction
import unittest

import so9_first_massive_spectrum as spectrum


class PhysicalRepresentationTests(unittest.TestCase):
    def test_chiral_cohomology_dimensions(self):
        characters = spectrum.physical_chiral_characters()
        self.assertEqual(
            {name: spectrum.character_dimension(characters[name]) for name in characters},
            {"44": 44, "84": 84, "128": 128, "NS": 128, "R": 128},
        )
        for name in ("44", "84", "128", "NS", "R"):
            self.assertTrue(all(mult > 0 for mult in characters[name].values()))

    def test_closed_sector_counts_and_statistics(self):
        closed = spectrum.closed_type_ii_characters()
        self.assertEqual(
            {name: spectrum.character_dimension(closed[name]) for name in ("NSNS", "RR", "NSR", "RNS")},
            {"NSNS": 16384, "RR": 16384, "NSR": 16384, "RNS": 16384},
        )
        self.assertEqual(spectrum.character_dimension(closed["signed"]), 0)

    def test_low_mixed_cartan_helicity_supertraces(self):
        chiral = spectrum.physical_chiral_characters()
        open_signed = spectrum.add_characters((1, chiral["NS"]), (-1, chiral["R"]))
        closed_signed = spectrum.closed_type_ii_characters()["signed"]
        self.assertEqual(spectrum.moment_residuals(open_signed, 8), {})
        self.assertEqual(spectrum.moment_residuals(closed_signed, 16), {})
        self.assertEqual(
            spectrum.signed_moment(open_signed, (8, 0, 0, 0)),
            Fraction(spectrum.factorial(8), 256),
        )
        self.assertEqual(
            spectrum.signed_moment(closed_signed, (16, 0, 0, 0)),
            Fraction(spectrum.factorial(16), 65536),
        )

    def test_exact_one_plane_factorisation(self):
        chiral = spectrum.physical_chiral_characters()
        open_signed = spectrum.add_characters((1, chiral["NS"]), (-1, chiral["R"]))
        closed_signed = spectrum.closed_type_ii_characters()["signed"]
        self.assertEqual(
            spectrum.one_plane_laurent(open_signed),
            spectrum.laurent_z_minus_inverse(8),
        )
        self.assertEqual(
            spectrum.one_plane_laurent(closed_signed),
            spectrum.laurent_z_minus_inverse(16),
        )


class PhysicalProjectorTests(unittest.TestCase):
    def test_symmetric_traceless_projector(self):
        result = spectrum.symmetric_traceless_projector_diagnostics()
        self.assertTrue(result.passed)
        self.assertEqual((result.ambient_dimension, result.trace), (81, 44))

    def test_three_form_projector(self):
        result = spectrum.three_form_projector_diagnostics()
        self.assertTrue(result.passed)
        self.assertEqual((result.ambient_dimension, result.trace), (729, 84))

    def test_gamma_traceless_vector_spinor_projector(self):
        result = spectrum.gamma_traceless_projector_diagnostics()
        self.assertTrue(result.passed)
        self.assertEqual((result.ambient_dimension, result.trace), (144, 128))


class RawModelNegativeControlTests(unittest.TestCase):
    def test_direct_raw_eight_field_character_factorises(self):
        self.assertEqual(
            spectrum.raw_eight_field_character(),
            spectrum.raw_eight_field_factorised_character(),
        )

    def test_raw_and_physical_characters_are_not_equal(self):
        raw = spectrum.raw_eight_field_character()
        physical = spectrum.closed_type_ii_characters()["signed"]
        self.assertNotEqual(raw, physical)
        self.assertEqual(
            spectrum.one_plane_laurent(raw),
            spectrum.laurent_z_minus_inverse(6, coefficient=-1024),
        )
        self.assertNotEqual(
            spectrum.one_plane_laurent(raw),
            spectrum.one_plane_laurent(physical),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
