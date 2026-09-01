import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY_ROOT / "scripts" / "validate_root_license_metadata.py"

VALID_FILES = {
    "Cargo.toml": '[package]\nname = "agentkit"\nlicense = "Apache-2.0"\n',
    "AGENTS.md": "# Agentora\n\n- License: `Apache-2.0`.\n",
    "CLAUDE.md": "| Field | Value |\n| --- | --- |\n| License | Apache-2.0 |\n",
    "CITATION.cff": 'cff-version: 1.2.0\nlicense: "Apache-2.0"\n',
    "ORIGIN.md": "# Origin\n\n- **License:** Apache-2.0\n",
}


class RootLicenseMetadataValidatorTests(unittest.TestCase):
    def run_validator(self, overrides=None):
        files = dict(VALID_FILES)
        files.update(overrides or {})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative_path, content in files.items():
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(VALIDATOR), str(root)],
                check=False,
                capture_output=True,
                text=True,
            )

    def assert_rejected(self, overrides, expected_message):
        result = self.run_validator(overrides)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected_message, result.stderr)

    def test_accepts_exact_root_metadata(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "Root package license metadata is consistent: Apache-2.0",
            result.stdout,
        )

    def test_ignores_preceding_workspace_license_and_rejects_wrong_package_license(self):
        self.assert_rejected(
            {
                "Cargo.toml": (
                    '[workspace.package]\nlicense = "Apache-2.0"\n\n'
                    '[package]\nname = "agentkit"\nlicense = "MIT"\n'
                )
            },
            "Cargo.toml [package].license must be exactly 'Apache-2.0'; found 'MIT'",
        )

    def test_rejects_missing_package_license(self):
        self.assert_rejected(
            {"Cargo.toml": '[package]\nname = "agentkit"\n'},
            "Cargo.toml is missing [package].license",
        )

    def test_rejects_duplicate_toml_license_key(self):
        self.assert_rejected(
            {
                "Cargo.toml": (
                    '[package]\nname = "agentkit"\nlicense = "Apache-2.0"\n'
                    'license = "MIT"\n'
                )
            },
            "Cargo.toml is invalid TOML",
        )

    def test_unrelated_apache_mention_does_not_hide_stale_authoritative_field(self):
        self.assert_rejected(
            {
                "AGENTS.md": (
                    "# Agentora\n\n- License: `MIT OR Apache-2.0`.\n\n"
                    "The dependency allowlist includes Apache-2.0.\n"
                )
            },
            "AGENTS.md License field must be exactly 'Apache-2.0'; found 'MIT OR Apache-2.0'",
        )

    def test_rejects_alternate_reordered_dual_license_spelling(self):
        self.assert_rejected(
            {"ORIGIN.md": "# Origin\n\n- **License:** Apache-2.0 OR MIT\n"},
            "ORIGIN.md License field must be exactly 'Apache-2.0'; found 'Apache-2.0 OR MIT'",
        )

    def test_rejects_duplicate_authoritative_fields_in_each_identity_file(self):
        duplicates = {
            "AGENTS.md": VALID_FILES["AGENTS.md"] + "- License: `Apache-2.0`.\n",
            "CLAUDE.md": VALID_FILES["CLAUDE.md"] + "| License | Apache-2.0 |\n",
            "CITATION.cff": VALID_FILES["CITATION.cff"] + 'license: "Apache-2.0"\n',
            "ORIGIN.md": VALID_FILES["ORIGIN.md"] + "- **License:** Apache-2.0\n",
        }
        for file_name, content in duplicates.items():
            with self.subTest(file_name=file_name):
                self.assert_rejected(
                    {file_name: content},
                    f"{file_name} must contain exactly one authoritative License field; found 2",
                )

    def test_rejects_multiline_pseudo_fields_in_each_identity_file(self):
        multiline_fields = {
            "AGENTS.md": "# Agentora\n\n- License:\n  `Apache-2.0`.\n",
            "CLAUDE.md": (
                "| Field | Value |\n| --- | --- |\n"
                "| License |\n  Apache-2.0 |\n"
            ),
            "CITATION.cff": "cff-version: 1.2.0\nlicense:\n  Apache-2.0\n",
            "ORIGIN.md": "# Origin\n\n- **License:**\n  Apache-2.0\n",
        }
        for file_name, content in multiline_fields.items():
            with self.subTest(file_name=file_name):
                self.assert_rejected(
                    {file_name: content},
                    f"{file_name} must contain exactly one authoritative License field; found 0",
                )


if __name__ == "__main__":
    unittest.main()
