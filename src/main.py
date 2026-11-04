"""Punto de entrada (también el de PyInstaller)."""

import sys

from pccf.app import main

if __name__ == "__main__":
    sys.exit(main())
