"""
FSA CLI Entry Point

Allows running the FSA CLI as a module:
    python -m agno.fsa [command] [args]
"""

import sys
from agno.fsa.cli import main

if __name__ == "__main__":
    sys.exit(main())
