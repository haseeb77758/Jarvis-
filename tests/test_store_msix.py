"""MSIX manifest/asset validation. Uses dummy binaries: no Microsoft account required."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_store_msix", ROOT / "tools" / "prepare_store_msix.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StoreMSIXTests(unittest.TestCase):
    def test_manifest_and_assets_generated_offline(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "built"
            source.mkdir()
            (source / "Jarvis.exe").write_bytes(b"test-binary")
            (source / "_internal").mkdir()
            (source / "_internal" / "library.dll").write_bytes(b"test-dll")
            output = Path(work) / "layout"
            module.prepare(source, output, "HaseebCrafts.Jarvis", "CN=12345-6789",
                           "1.0.0.0", "Haseeb Crafts")
            self.assertEqual((output / "Jarvis.exe").read_bytes(), b"test-binary")
            self.assertTrue((output / "_internal" / "library.dll").is_file())
            xml = ET.parse(output / "AppxManifest.xml")
            ns = {"a": module.PACKAGE_NS, "uap10": module.UAP10_NS,
                  "rescap": module.RESCAP_NS}
            ident = xml.find("a:Identity", ns)
            self.assertEqual(ident.attrib["Name"], "HaseebCrafts.Jarvis")
            app = xml.find("a:Applications/a:Application", ns)
            self.assertEqual(app.attrib[f"{{{module.UAP10_NS}}}RuntimeBehavior"], "packagedClassicApp")
            self.assertIsNotNone(xml.find(".//rescap:Capability", ns))
            for name in ("StoreLogo.png", "SmallLogo.png", "TileLogo.png"):
                png = (output / "Assets" / name).read_bytes()
                self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
                self.assertGreater(len(png), 100)

    def test_invalid_store_identifiers_rejected_before_write(self):
        for name, publisher, version in [
            ("x", "CN=Publisher", "1.0.0.0"),
            ("Haseeb.Jarvis", "", "1.0.0.0"),
            ("Haseeb.Jarvis", "CN=Publisher", "1.0.0"),
            ("Haseeb.Jarvis", "CN=Publisher", "1.0.0.65536"),
        ]:
            with self.subTest(name=name, version=version), self.assertRaises(ValueError):
                module.validate_identity(name, publisher, version)

    def test_missing_real_build_never_claimed_ready(self):
        with tempfile.TemporaryDirectory() as work:
            source = Path(work) / "source"
            source.mkdir()
            with self.assertRaises(FileNotFoundError):
                module.prepare(source, Path(work) / "out",
                               "Haseeb.Jarvis", "CN=Publisher", "1.0.0.0")
if __name__ == "__main__":
    unittest.main()
