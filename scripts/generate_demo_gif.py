#!/usr/bin/env python3
"""
Generate animated terminal demo GIF for Skills Catalog Governance.
Creates a realistic terminal animation showing the governance pipeline execution.
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageSequence
except ImportError:
    print("Pillow not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])
    from PIL import Image, ImageDraw, ImageFont, ImageSequence


# Configuration
WIDTH = 900
HEIGHT = 500
FPS = 2
FRAME_DELAY = int(1000 / FPS)  # ms per frame
BG_COLOR = "#0d1117"
TEXT_COLOR = "#e6edf3"
PROMPT_COLOR = "#58a6ff"
COMMAND_COLOR = "#d29922"
OUTPUT_COLOR = "#8b949e"
SUCCESS_COLOR = "#3fb950"
ACCENT_COLOR = "#a371f7"
CURSOR_COLOR = "#58a6ff"

# Terminal font - use monospace
FONT_SIZE = 14
try:
    # Try to find a monospace font
    FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", FONT_SIZE)
    FONT_BOLD = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", FONT_SIZE)
except:
    try:
        FONT = ImageFont.truetype("C:/Windows/Fonts/CascadiaCode.ttf", FONT_SIZE)
        FONT_BOLD = ImageFont.truetype("C:/Windows/Fonts/CascadiaCode.ttf", FONT_SIZE)
    except:
        FONT = ImageFont.load_default()
        FONT_BOLD = ImageFont.load_default()


def create_terminal_frame(lines, cursor_pos=None, cursor_visible=True, show_label=False):
    """Create a single terminal frame."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Draw subtle grid lines
    for y in range(0, HEIGHT, 24):
        draw.line([(0, y), (WIDTH, y)], fill="#1f2937", width=1)
    
    y_offset = 20
    for i, line in enumerate(lines):
        color = TEXT_COLOR
        font = FONT
        
        if line.startswith("$ "):
            color = PROMPT_COLOR
            font = FONT_BOLD
        elif line.startswith("  ") and "→" in line:
            color = ACCENT_COLOR
        elif "PASS" in line or "✓" in line:
            color = SUCCESS_COLOR
        elif "ERROR" in line or "FAIL" in line:
            color = "#f85149"
        elif line.startswith("  ") and any(c.isdigit() for c in line):
            color = OUTPUT_COLOR
        
        draw.text((20, y_offset), line, font=font, fill=color)
        y_offset += 22
    
    # Draw label at bottom
    if show_label:
        label_text = "ILLUSTRATIVE REPLAY — based on actual pilot evidence"
        bbox = draw.textbbox((0, 0), label_text, font=FONT)
        label_x = WIDTH - bbox[2] - 20
        # Background pill
        draw.rounded_rectangle(
            [label_x - 8, HEIGHT - 34, WIDTH - 12, HEIGHT - 8],
            radius=4, fill="#2d3748",
        )
        draw.text((label_x, HEIGHT - 30), label_text, font=FONT, fill="#a371f7")
    
    # Draw cursor
    if cursor_visible and cursor_pos is not None:
        line_idx, char_idx = cursor_pos
        if line_idx < len(lines):
            line = lines[line_idx]
            # Calculate cursor position
            text_before = line[:char_idx]
            bbox = draw.textbbox((0, 0), text_before, font=FONT_BOLD if line.startswith("$ ") else FONT)
            cursor_x = 20 + bbox[2]
            cursor_y = 20 + line_idx * 22
            draw.rectangle([cursor_x, cursor_y, cursor_x + 2, cursor_y + 20], fill=CURSOR_COLOR)
    
    return img


def generate_demo_frames():
    """Generate all frames for the demo animation."""
    frames = []
    
    # Scene 1: Initial prompt
    scene1 = [
        "",
        "  Skills Catalog Governance  —  Agent Skill Pipeline",
        "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "$ detect-skills",
        "",
        "  Scanning skill stores...",
        "  ┌──────────────┬───────┐",
        "  │ Store        │ Count │",
        "  ├──────────────┼───────┤",
        "  │ Hermes       │    73 │",
        "  │ Claude Code  │    41 │",
        "  │ OpenCode     │    36 │",
        "  │ Codex        │    28 │",
        "  │ Other        │    33 │",
        "  ├──────────────┼───────┤",
        "  │ TOTAL        │   211 │",
        "  └──────────────┴───────┘",
        "",
        "  ✓ 211 skills discovered — 0 errors",
        "",
        "$ ",
    ]
    
    # Build scene 1 progressively
    for i in range(1, len(scene1) + 1):
        cursor = (i - 1, len(scene1[i-1])) if i == len(scene1) else None
        frames.append(create_terminal_frame(scene1[:i], cursor, i == len(scene1)))
    
    # Hold final frame
    for _ in range(6):
        frames.append(create_terminal_frame(scene1, (len(scene1)-1, 0), True))
    
    # Scene 2: detect-groups
    scene2 = scene1[:-1] + [
        "$ detect-groups --inventory inventory.json --overlap-threshold 0.50",
        "",
        "  Computing pairwise similarity...",
        "  ┌────────────────────────────────────┐",
        "  │ Pairs analyzed:     22,155         │",
        "  │ Cosine threshold:   0.30           │",
        "  │ Overlap threshold:  0.50           │",
        "  │ Max group size:     8              │",
        "  └────────────────────────────────────┘",
        "",
        "  ✓ 89 candidate pairs → 19 families (strong-pair only)",
        "  ⚠ 0 oversized groups",
        "",
        "$ ",
    ]
    
    for i in range(len(scene1), len(scene2) + 1):
        cursor = (i - 1, len(scene2[i-1])) if i == len(scene2) else None
        frames.append(create_terminal_frame(scene2[:i], cursor, i == len(scene2)))
    
    for _ in range(6):
        frames.append(create_terminal_frame(scene2, (len(scene2)-1, 0), True))
    
    # Scene 3: council
    scene3 = scene2[:-1] + [
        "$ council --group commit-message-family",
        "",
        "  ┌─ COUNCIL SESSION ────────────────────────┐",
        "  │ 5 advisors  •  5 anonymous reviews  •  1 chairman",
        "  ├────────────────────────────────────────────┤",
        "  │ Advisor 1 (Architect):    MERGE generators │",
        "  │ Advisor 2 (Security):     SPLIT executor   │",
        "  │ Advisor 3 (Maintainer):   MERGE generators │",
        "  │ Advisor 4 (Performance):  MERGE generators │",
        "  │ Advisor 5 (User):         RECAT executor   │",
        "  ├────────────────────────────────────────────┤",
        "  │ Chairman synthesis: MERGE 2 generators,    │",
        "  │                     KEEP_SEPARATE executor │",
        "  └────────────────────────────────────────────┘",
        "",
        "  Verdict: MERGE + RECATEGORIZE",
        "",
        "$ ",
    ]
    
    for i in range(len(scene2), len(scene3) + 1):
        cursor = (i - 1, len(scene3[i-1])) if i == len(scene3) else None
        frames.append(create_terminal_frame(scene3[:i], cursor, i == len(scene3)))
    
    for _ in range(6):
        frames.append(create_terminal_frame(scene3, (len(scene3)-1, 0), True))
    
    # Scene 4: golden-gate
    scene4 = scene3[:-1] + [
        "$ golden-gate --manifest golden.json --workdir ./work",
        "",
        "  Runner execution enabled (allow_runners: true)",
        "  Testing 6 fixed inputs against 2 sources...",
        "",
        "  ┌────────────────────────────────────────────┐",
        "  │ Input           │ Source A │ Master │ ✓   │",
        "  ├─────────────────┼──────────┼────────┼─────┤",
        "  │ format:conventional│  OK     │  OK    │ MATCH│",
        "  │ format:angular     │  OK     │  OK    │ MATCH│",
        "  │ format:emoji       │  OK     │  OK    │ MATCH│",
        "  │ format:scrum       │  OK     │  OK    │ MATCH│",
        "  │ format:jira        │  OK     │  OK    │ MATCH│",
        "  │ format:github      │  OK     │  OK    │ MATCH│",
        "  └────────────────────────────────────────────┘",
        "",
        "  ✓ 6 / 6 outputs reproduced — absorption authorized",
        "",
        "$ ",
    ]
    
    for i in range(len(scene3), len(scene4) + 1):
        cursor = (i - 1, len(scene4[i-1])) if i == len(scene4) else None
        frames.append(create_terminal_frame(scene4[:i], cursor, i == len(scene4)))
    
    for _ in range(6):
        frames.append(create_terminal_frame(scene4, (len(scene4)-1, 0), True))
    
    # Scene 5: benchmark
    scene5 = scene4[:-1] + [
        "$ benchmark --bundle docs/benchmark.json",
        "",
        "  G2 Benchmark: master vs 2 sources + baseline",
        "  Runs per cell: 3  |  Cells: 36",
        "",
        "  ┌────────────────────────────────────────────┐",
        "  │ Cell              │ Master │ Source A │ B  │",
        "  ├───────────────────┼────────┼──────────┼────┤",
        "  │ format:conventional│   WIN   │   LOSS   │ TIE│",
        "  │ format:angular     │   WIN   │   LOSS   │ WIN│",
        "  │ ... (36 cells)     │  36/36  │  12/36   │ 18 │",
        "  └────────────────────────────────────────────┘",
        "",
        "  ✓ Master wins or ties every cell",
        "  ✓ Master beats best source overall",
        "  ✓ 36 / 36 cells PASS — GO",
        "",
        "$ ",
    ]
    
    for i in range(len(scene4), len(scene5) + 1):
        cursor = (i - 1, len(scene5[i-1])) if i == len(scene5) else None
        frames.append(create_terminal_frame(scene5[:i], cursor, i == len(scene5)))
    
    for _ in range(6):
        frames.append(create_terminal_frame(scene5, (len(scene5)-1, 0), True))
    
    # Scene 6: promote
    scene6 = scene5[:-1] + [
        "$ verify-approval --draft master.SKILL.md --approval approval.json",
        "",
        "  Verifying hash-bound approval...",
        "  ✓ draft_sha256 matches live draft",
        "  ✓ loss-report re-verified: all PASS",
        "  ✓ no source tampering detected",
        "",
        "$ apply-moves --plan plan.json --apply --yes",
        "",
        "  ┌────────────────────────────────────────────┐",
        "  │ Moving 2 skills to archive...              │",
        "  ├────────────────────────────────────────────┤",
        "  │ canonical-commit-message  →  archive/ ✓    │",
        "  │ ce-commit-executor        →  archive/ ✓    │",
        "  └────────────────────────────────────────────┘",
        "",
        "  ✓ 2 survivors promoted",
        "  ✓ 191 skills archived to skills-archive/",
        "  ✓ Post-promotion audit: all hashes verified",
        "",
        "  ┌────────────────────────────────────────────┐",
        "  │ PIPELINE COMPLETE — CANONICAL CATALOG READY│",
        "  └────────────────────────────────────────────┘",
        "",
        "$ ",
    ]
    
    for i in range(len(scene5), len(scene6) + 1):
        cursor = (i - 1, len(scene6[i-1])) if i == len(scene6) else None
        frames.append(create_terminal_frame(scene6[:i], cursor, i == len(scene6)))
    
    for _ in range(10):
        frames.append(create_terminal_frame(scene6, (len(scene6)-1, 0), True, show_label=True))
    
    return frames


def main():
    output_dir = Path("assets/demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "governance-pipeline.gif"
    
    print("Generating terminal demo frames...")
    frames = generate_demo_frames()
    print(f"Generated {len(frames)} frames")
    
    print("Saving GIF...")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_DELAY,
        loop=0,
        optimize=True,
        disposal=2,
    )
    
    # Check file size
    size_kb = output_path.stat().st_size / 1024
    print(f"Saved to {output_path} ({size_kb:.1f} KB)")
    
    # Also save a static preview frame (first frame of final scene)
    preview_path = output_dir / "governance-pipeline-preview.png"
    frames[-1].save(preview_path)
    print(f"Preview saved to {preview_path}")
    
    return output_path


if __name__ == "__main__":
    main()