from pathlib import Path
import csv
import tempfile
import unittest

from main import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


class PipelineTest(unittest.TestCase):
    def test_sample_csv_has_nine_unique_rows(self):
        with (ROOT / "data/sample/recruiter.csv").open("r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        emails = [row["email"].strip().lower() for row in rows]
        self.assertEqual(len(rows), 9)
        self.assertEqual(len(emails), len(set(emails)))

    def test_default_pipeline_builds_canonical_profile(self):
        canonical, output = run_pipeline(ROOT / "data/sample/recruiter.csv", ROOT / "data/sample/notes.txt")

        self.assertEqual(output, canonical)
        self.assertEqual(canonical["full_name"], "Aarush Malhotra")
        self.assertEqual(canonical["emails"][0], "aarush.malhotra@gmail.com")
        self.assertEqual(canonical["phones"][0], "+919876543210")
        self.assertEqual(canonical["location"]["country"], "IN")
        self.assertGreaterEqual(
            {skill["name"] for skill in canonical["skills"]},
            {"Python", "SQL", "Spark", "AWS"},
        )
        self.assertEqual(len(canonical["experience"]), 1)
        self.assertTrue(canonical["provenance"])
        self.assertGreater(canonical["overall_confidence"], 0)
        self.assertLessEqual(canonical["overall_confidence"], 1)

    def test_custom_projection_selects_and_renames_fields(self):
        _, output = run_pipeline(
            ROOT / "data/sample/recruiter.csv",
            ROOT / "data/sample/notes.txt",
            ROOT / "data/sample/config_custom.json",
        )

        self.assertEqual(output["full_name"], "Aarush Malhotra")
        self.assertEqual(output["primary_email"], "aarush.malhotra@gmail.com")
        self.assertEqual(output["phone"], "+919876543210")
        self.assertEqual(output["city"], "Bengaluru")
        self.assertIn("Python", output["skills"])
        self.assertNotIn("provenance", output)
        self.assertIn("overall_confidence", output)

    def test_batch_pipeline_outputs_all_note_candidates(self):
        canonical_profiles, outputs = run_pipeline(
            ROOT / "data/sample/recruiter.csv",
            ROOT / "data/sample/notes.txt",
            ROOT / "data/sample/config_custom.json",
            all_candidates=True,
        )

        names = {profile["full_name"] for profile in canonical_profiles}
        expected_names = {
            "Aarush Malhotra",
            "Diya Nair",
            "Vivaan Roy",
            "Anika Sharma",
            "Kunal Mehta",
            "Ishita Banerjee",
            "Raghav Bhatia",
            "Meera Iyer",
            "Aditya Kulkarni",
        }
        self.assertEqual(len(canonical_profiles), 9)
        self.assertEqual(len(outputs), 9)
        self.assertEqual(names, expected_names)

    def test_missing_sources_degrade_gracefully(self):
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            missing_csv = temp_dir / "missing.csv"
            empty_notes = temp_dir / "notes.txt"
            empty_notes.write_text("", encoding="utf-8")

            canonical, _ = run_pipeline(missing_csv, empty_notes)

        self.assertTrue(canonical["candidate_id"].startswith("cand_"))
        self.assertEqual(canonical["emails"], [])
        self.assertEqual(canonical["overall_confidence"], 0.0)
        self.assertTrue(any("csv file missing" in warning for warning in canonical["warnings"]))
        self.assertTrue(any("notes file empty" in warning for warning in canonical["warnings"]))


if __name__ == "__main__":
    unittest.main()
