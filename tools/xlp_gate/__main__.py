"""Executable module entry point for `python3 -m tools.xlp_gate`."""

from __future__ import annotations

import sys

from tools.xlp_gate.cli import main

if __name__ == "__main__":
    sys.exit(main())
