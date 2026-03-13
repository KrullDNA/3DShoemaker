# -*- coding: utf-8 -*-
"""Create the top piece

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateTopPiece"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateTopPiece invoked.")
    Rhino.RhinoApp.WriteLine("  Create the top piece")
    return 0
