#!/usr/bin/env python3
"""Launcher for the canonical root linkify_defined_terms.py script."""

from pathlib import Path
import runpy

here = Path(__file__).resolve()
for base in here.parents:
    candidate = base / "scripts" / "linkify_defined_terms.py"
    if candidate.exists() and candidate != here:
        runpy.run_path(str(candidate), run_name="__main__")
        break
else:
    raise SystemExit("Could not find repository root scripts/linkify_defined_terms.py")
