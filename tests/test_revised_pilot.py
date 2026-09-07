from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from revised_pilot import selected_method


class RevisedPilotChecks(unittest.TestCase):
    def test_pilot_requires_same_revision_to_pass_both_controls(self):
        confirmation = dict(
            selected_for_exploratory_pilot="coarse_only",
            assessment_gate_passed=True,
            gates={"coarse_only": {"passed": True}},
            errors=[],
        )
        control = dict(
            rows=[
                dict(
                    method="coarse_only",
                    matches=[dict(toi=700.02, strict=True, all_screening_checks=True)],
                )
            ]
        )
        audit = dict(passed=True)
        self.assertEqual(selected_method(confirmation, control, audit), "coarse_only")
        for field, value in [
            ("assessment_gate_passed", False),
            ("selected_for_exploratory_pilot", None),
            ("errors", ["failed computation"]),
        ]:
            changed = dict(confirmation, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                selected_method(changed, control, audit)
        for field, value in [("toi", 700.04), ("strict", False), ("all_screening_checks", False)]:
            changed = deepcopy(control)
            changed["rows"][0]["matches"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                selected_method(confirmation, changed, audit)
        changed = deepcopy(control)
        changed["rows"][0]["method"] = "qualified_seeds"
        with self.assertRaises(ValueError):
            selected_method(confirmation, changed, audit)
        with self.assertRaises(ValueError):
            selected_method(confirmation, control, dict(passed=False))


if __name__ == "__main__":
    unittest.main()
