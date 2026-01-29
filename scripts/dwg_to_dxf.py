#!/usr/bin/env python3
"""Simple DWG to DXF converter using LibreDWG (brew install libredwg)"""

import subprocess
import sys
from pathlib import Path


def convert(dwg_path: str) -> None:
    input_file = Path(dwg_path).resolve()

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    output_file = input_file.with_suffix(".dxf")

    print(f"Converting: {input_file.name}")

    # Use locally built LibreDWG
    dwg2dxf = "/tmp/libredwg/programs/dwg2dxf"

    result = subprocess.run(
        [dwg2dxf, "-o", str(output_file), str(input_file)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0 and output_file.exists():
        print(f"✓ Done: {output_file}")
    else:
        print(f"✗ Failed: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dwg_to_dxf.py <path_to_dwg>")
        sys.exit(1)

    convert(sys.argv[1])
