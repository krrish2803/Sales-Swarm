from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path so imports like graph, models, agents work
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from main import app  # noqa: E402, F401
