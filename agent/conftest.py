"""Pytest configuration for agent tests."""

import sys
from pathlib import Path

# Add scripts directory to path so imports work
scripts_dir = Path(__file__).parent / 'scripts'
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
