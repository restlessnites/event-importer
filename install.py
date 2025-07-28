#!/usr/bin/env python3
"""Event Importer Installation Script."""

import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from installer.core import main

if __name__ == "__main__":
    main()
