#!/usr/bin/env python3
import argparse
import re
import sys
import tomllib
from pathlib import Path


EXPECTED_LICENSE = "Apache-2.0"

IDENTITY_FIELDS = {
    "AGENTS.md": re.compile(r"^-\s+License:\s*(.*?)\s*$", re.MULTILINE),
    "CLAUDE.md": re.compile(
        r"^\|\s*License\s*\|\s*(.*?)\s*\|\s*$", re.MULTILINE
    ),
    "CITATION.cff": re.compile(r"^license:\s*(.*?)\s*$", re.MULTILINE),
    "ORIGIN.md": re.compile(r"^-\s+\*\*License:\*\*\s*(.*?)\s*$", re.MULTILINE),
}


def normalized_value(file_name, value):
    if file_name == "AGENTS.md" and value.endswith("."):
        value = value[:-1].rstrip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"`":
        value = value[1:-1]
    return value


def validate_cargo_toml(repository_root):
    cargo_path = repository_root / "Cargo.toml"
    try:
        with cargo_path.open("rb") as cargo_file:
            document = tomllib.load(cargo_file)
    except FileNotFoundError:
        return ["Cargo.toml is missing"]
    except tomllib.TOMLDecodeError as error:
        return [f"Cargo.toml is invalid TOML: {error}"]

    package = document.get("package")
    if not isinstance(package, dict) or "license" not in package:
        return ["Cargo.toml is missing [package].license"]

    package_license = package["license"]
    if package_license != EXPECTED_LICENSE:
        return [
            "Cargo.toml [package].license must be exactly "
            f"'{EXPECTED_LICENSE}'; found {package_license!r}"
        ]
    return []


def validate_identity_file(repository_root, file_name, pattern):
    path = repository_root / file_name
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"{file_name} is missing"]

    values = pattern.findall(content)
    if len(values) != 1:
        return [
            f"{file_name} must contain exactly one authoritative License field; "
            f"found {len(values)}"
        ]

    value = normalized_value(file_name, values[0])
    if value != EXPECTED_LICENSE:
        return [
            f"{file_name} License field must be exactly '{EXPECTED_LICENSE}'; "
            f"found {value!r}"
        ]
    return []


def validate(repository_root):
    errors = validate_cargo_toml(repository_root)
    for file_name, pattern in IDENTITY_FIELDS.items():
        errors.extend(validate_identity_file(repository_root, file_name, pattern))
    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate Agentora root Apache-2.0 metadata"
    )
    parser.add_argument(
        "repository_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    repository_root = parser.parse_args().repository_root.resolve()
    errors = validate(repository_root)
    if errors:
        for error in errors:
            file_name = error.split(" ", 1)[0]
            print(f"::error file={file_name}::{error}", file=sys.stderr)
        return 1

    print(f"Root package license metadata is consistent: {EXPECTED_LICENSE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
