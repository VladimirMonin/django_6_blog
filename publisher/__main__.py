"""Allow running as ``python -m publisher``."""

import sys

from .cli import main

sys.exit(main())