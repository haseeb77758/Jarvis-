"""Offline Microsoft Store pre-submission checklist for the Jarvis project.

No Partner Center account, certificate, secrets, installation or uploads required.
This validates project structure and document readiness, not Store certification.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "app.py", "core.py", "dashboard.py", "desktop.py", "memory.py", "voice.py",
    ".github/workflows/store-msix.yml", "tools/prepare_store_msix.py",
    "tests/test_store_msix.py", "STORE-LISTING-DRAFT.md",
    "STORE-PRIVACY-DRAFT.md", "PERSONAL-STORE-TEST.md",
    "MICROSOFT-STORE-SETUP.md",
)
PRIVACY_MARKERS = (
    "[LEGAL NAME OF INDIVIDUAL DEVELOPER",
    "[EFFECTIVE DATE",
    "[REAL CONTACT EMAIL",
    "[STABLE PUBLIC HTTPS URL",
)
LISTING_MARKERS = (
    "Privacy policy URL:",
    "Support contact:",
    "Screenshot:",
)


def examine(root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors = []
    ready_later = []
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"Missing required Store preparation file: {relative}")
    listing = root / "STORE-LISTING-DRAFT.md"
    privacy = root / "STORE-PRIVACY-DRAFT.md"
    if listing.is_file():
        data = listing.read_text(encoding="utf-8")
        for marker in LISTING_MARKERS:
            if marker not in data:
                errors.append(f"Listing lacks a required field label: {marker}")
        if "Store certification" not in data and "Store listing" not in data:
            errors.append("Listing does not explain Store certification.")
    if privacy.is_file():
        data = privacy.read_text(encoding="utf-8")
        for term in ("Microphone", "LOCALAPPDATA", "Ollama", "Google", "WhatsApp"):
            if term.casefold() not in data.casefold():
                errors.append(f"Privacy draft missing disclosed topic: {term}")
        for marker in PRIVACY_MARKERS:
            if marker in data:
                ready_later.append("Complete publisher-only privacy field: " + marker)
    workflow = root / ".github/workflows/store-msix.yml"
    if workflow.is_file():
        data = workflow.read_text(encoding="utf-8")
        for term in ("inputs.package_identity", "inputs.publisher", "SUBMISSION-ONLY", "makeappx"):
            if term not in data:
                errors.append("Store packaging workflow missing: " + term)
    ready_later.extend((
        "Microsoft Individual developer identity verification",
        "Reserve HASEEB AI Jarvis name and copy exact Partner Center package identity + publisher",
        "Publish privacy policy on a real public HTTPS URL after legal review",
        "Capture real app screenshots on the approved Store-candidate Windows build",
        "Select supported private-audience settings and finish Store questionnaire",
        "Submit Store candidate to Microsoft and pass certification/signing",
        "Verify installation on the target Windows 11 laptop with Smart App Control on",
    ))
    return errors, ready_later


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Exit nonzero for missing repository assets.")
    args = parser.parse_args()
    errors, remaining = examine()
    for issue in errors:
        print("ERROR:", issue)
    for issue in remaining:
        print("OWNER ACTION:", issue)
    if not errors:
        print("PASS: Offline repository Store preparation checks. No claim of publication or approval.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
