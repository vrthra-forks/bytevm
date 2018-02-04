"""A main program for Bytevm."""

import sys

from . import execfile
execfile.ExecFile().cmdline(sys.argv)
