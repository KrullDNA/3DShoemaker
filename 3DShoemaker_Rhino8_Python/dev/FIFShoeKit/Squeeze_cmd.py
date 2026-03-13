# -*- coding: utf-8 -*-
"""Squeeze/compress geometry

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "Squeeze"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Squeeze invoked.")
    Rhino.RhinoApp.WriteLine("  Squeeze/compress geometry")
    return 0
