"""Verify an allowlisted Jarvis source archive and its internal SHA256 manifest."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
from zipfile import ZipFile
from package_source import FOLDER, FILES, source_files, ROOT


def verify(path: Path) -> int:
    expected = {f"{FOLDER}/{p.as_posix()}" for p in source_files(ROOT)}
    expected.update({f"{FOLDER}/README-START-HERE.txt", f"{FOLDER}/PACKAGE-MANIFEST.txt"})
    with ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Unexpected or missing files in source bundle.")
        manifest = z.read(f"{FOLDER}/PACKAGE-MANIFEST.txt").decode("utf-8")
        for name in expected:
            if name.endswith("PACKAGE-MANIFEST.txt"):
                continue
            if ".." in Path(name).parts or name.startswith("/"):
                raise ValueError("Unsafe archive path.")
            if not name.endswith("README-START-HERE.txt"):
                relative = name[len(FOLDER) + 1:]
                digest = hashlib.sha256(z.read(name)).hexdigest()
                if f"{digest}   {relative}" not in manifest:
                    raise ValueError("Checksum mismatch: " + relative)
    print(f"PASS: {len(expected)} archive entries; no executable or secret files.")
    return len(expected)


if __name__ == "__main__":
    verify(Path(sys.argv[1]))
