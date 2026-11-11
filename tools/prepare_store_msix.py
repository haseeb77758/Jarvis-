"""Prepare a Microsoft Store MSIX layout for the existing Jarvis Windows build.

Store certification and signing happen in Partner Center, not in this script.
An unsigned MSIX produced here must NOT be sideloaded on user devices.
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

PACKAGE_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP_NS = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
UAP10_NS = "http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
RESCAP_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")
VERSION_PATTERN = re.compile(r"^(?:0|[1-9]\d{0,4})(?:\.(?:0|[1-9]\d{0,4})){3}$")


def validate_identity(name: str, publisher: str, version: str) -> None:
    if not ID_PATTERN.fullmatch(name) or name.endswith("."):
        raise ValueError("Package identity must match the exact Partner Center name.")
    if not publisher.startswith("CN=") or not 3 <= len(publisher) <= 200:
        raise ValueError("Publisher must be the exact Partner Center Publisher value, starting with CN=.")
    if any(ord(c) < 32 or c in '<>&"\\' for c in publisher):
        raise ValueError("Invalid publisher attribute.")
    if not VERSION_PATTERN.fullmatch(version) or any(int(x) > 65535 for x in version.split(".")):
        raise ValueError("Version must have four integer components (each 0–65535).")


def png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def generate_logo(size: int) -> bytes:
    """Lightweight opaque square H mark, no external dependencies."""
    if size < 8:
        raise ValueError("Logo too small.")
    raw = bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            l = size // 5
            right = size - l - 1
            top = size // 5
            bottom = size - top
            is_h = top <= y < bottom and (
                l <= x < l + max(2, size // 8)
                or right - max(2, size // 8) < x <= right
                or abs(y - size // 2) <= max(1, size // 14) and l <= x <= right
            )
            raw.extend((56, 222, 213) if is_h else (8, 17, 27))
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))


def prepare(source: Path, output: Path, identity: str, publisher: str,
            version: str, publisher_display: str = "Haseeb Crafts") -> Path:
    validate_identity(identity, publisher, version)
    source = source.resolve()
    output = output.resolve()
    if not (source / "Jarvis.exe").is_file():
        raise FileNotFoundError("Build a verified onedir Jarvis.exe before MSIX packaging.")
    if output == source or output in source.parents or source in output.parents:
        raise ValueError("Output and source must be separate directories.")
    if any(c in publisher_display for c in "<>&") or not publisher_display.strip():
        raise ValueError("Publisher display name invalid.")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output, symlinks=False)
    assets = output / "Assets"
    assets.mkdir(exist_ok=True)
    for size, filename in [(50, "StoreLogo.png"), (44, "SmallLogo.png"), (150, "TileLogo.png")]:
        (assets / filename).write_bytes(generate_logo(size))
    manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<Package
 xmlns="{PACKAGE_NS}"
 xmlns:uap="{UAP_NS}"
 xmlns:uap10="{UAP10_NS}"
 xmlns:rescap="{RESCAP_NS}"
 IgnorableNamespaces="uap10 rescap">
  <Identity Name={quoteattr(identity)}
            Publisher={quoteattr(publisher)}
            Version={quoteattr(version)}
            ProcessorArchitecture="x64"/>
  <Properties>
    <DisplayName>HASEEB AI Jarvis</DisplayName>
    <PublisherDisplayName>{escape(publisher_display)}</PublisherDisplayName>
    <Description>Local Windows desktop AI assistant</Description>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>
  <Resources><Resource Language="en-us"/></Resources>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop"
      MinVersion="10.0.19041.0" MaxVersionTested="10.0.26100.0"/>
  </Dependencies>
  <Applications>
    <Application Id="Jarvis" Executable="Jarvis.exe"
      uap10:RuntimeBehavior="packagedClassicApp" uap10:TrustLevel="mediumIL">
      <uap:VisualElements DisplayName="HASEEB AI Jarvis"
        Description="Jarvis local desktop assistant"
        Square150x150Logo="Assets\\TileLogo.png"
        Square44x44Logo="Assets\\SmallLogo.png"
        BackgroundColor="#08111B"/>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust"/>
    <DeviceCapability Name="microphone"/>
  </Capabilities>
</Package>
"""
    path = output / "AppxManifest.xml"
    path.write_text(manifest, encoding="utf-8")
    ET.parse(path)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Store-ready package contents; not a signed installer.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--identity", required=True, help="Exact Partner Center package identity")
    parser.add_argument("--publisher", required=True, help="Exact Partner Center Publisher (CN=...)")
    parser.add_argument("--version", default="1.0.0.0")
    parser.add_argument("--publisher-display", default="Haseeb Crafts")
    args = parser.parse_args()
    result = prepare(args.source, args.output, args.identity, args.publisher,
                     args.version, args.publisher_display)
    print(f"Store MSIX source layout ready: {result}")
    print("Unsigned output is for Store submission only. Do NOT sideload it.")
