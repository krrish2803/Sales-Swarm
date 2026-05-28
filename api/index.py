from __future__ import annotations

import os
import sys

_current = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_current)
if _root not in sys.path:
    sys.path.insert(0, _root)

from main import app as _app

app = _app
