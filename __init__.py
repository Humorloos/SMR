import sys

if 'pytest' not in sys.modules:
    from .smr import main
