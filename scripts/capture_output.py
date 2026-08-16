#!/usr/bin/env python3
"""Capture real check-package output as a terminal screenshot."""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

WIDTH = 840
HEIGHT = 320
BG = "#0d1117"
try:
    FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
    FONT_BOLD = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 13)
except Exception:
    FONT = ImageFont.load_default()
    FONT_BOLD = FONT

root = Path(__file__).resolve().parents[1]
result = subprocess.run(
    [sys.executable, str(root / "scripts" / "catalog_governance.py"), "check-package", "--root", "."],
    capture_output=True, text=True, cwd=str(root),
)
output = result.stdout.strip()
data = json.loads(output)
status = data.get("status", "FAIL")
skills = data.get("skill_sha256", "")[:16]

# Build terminal lines
lines = [
    "",
    "  Skills Catalog Governance  —  Package Verification",
    "  ──────────────────────────────────────────────────",
    "",
    "  $ python3 check-package --root .",
    "",
]

if status == "PASS":
    lines.append(f"  ✓ Package verification: {status}")
    lines.append("  ✓ SKILL.md SHA-256: " + skills + "...")
    lines.append("  ✓ " + str(len(data.get('required_files', []))) + " required files present")
    lines.append("  ✓ All schemas valid JSON")
    lines.append("")
    lines.append("  Pipeline ready. You can now run detect-skills.")
else:
    lines.append(f"  ✗ Package verification: {status}")
    missing = data.get("missing_files", [])
    invalid = data.get("invalid_files", [])
    for f in missing:
        lines.append(f"    missing: {f}")
    for f in invalid:
        lines.append(f"    invalid: {f}")

# Render
img = Image.new("RGB", (WIDTH, HEIGHT), BG)
draw = ImageDraw.Draw(img)

# Grid
for y in range(0, HEIGHT, 24):
    draw.line([(0, y), (WIDTH, y)], fill="#1f2937", width=1)

y = 20
for line in lines:
    color = "#e6edf3"
    font = FONT
    if line.startswith("  $"):
        color = "#58a6ff"
        font = FONT_BOLD
    elif "✓" in line:
        color = "#3fb950"
    elif "✗" in line:
        color = "#f85149"
    elif "───" in line:
        color = "#30363d"
    draw.text((20, y), line, font=font, fill=color)
    y += 22

output_path = root / "assets" / "demo" / "check-package-output.png"
img.save(output_path)
print(f"Saved to {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
print(f"Status: {status} | Files: {len(data.get('required_files', []))}")