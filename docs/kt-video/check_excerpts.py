"""Check that every code line shown in kt-video.html matches the real source file, line for line."""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXCERPTS = {"cite_or_refuse/verifier.py": "SCENES[\"05\"]"}


def main() -> int:
    html = (HERE / "kt-video.html").read_text(encoding="utf-8")
    bad = 0
    for path, marker in EXCERPTS.items():
        block = html[html.index(marker):]
        block = block[block.index("const CODE = ["):block.index("];")]
        source = (REPO / path).read_text(encoding="utf-8").splitlines()
        for n, text in re.findall(r"\[(\d+), ['`](.*?)['`]\]", block):
            if source[int(n) - 1] != text:
                bad += 1
                print(f"MISMATCH {path}:{n}\n  shown:  {text}\n  source: {source[int(n) - 1]}")
    print("excerpts OK" if not bad else f"{bad} mismatched line(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
