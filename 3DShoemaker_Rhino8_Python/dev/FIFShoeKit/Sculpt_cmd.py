# -*- coding: utf-8 -*-
"""Sculpt surfaces interactively

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "Sculpt"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Sculpt invoked.")
    Rhino.RhinoApp.WriteLine("  Sculpt surfaces interactively")
    return 0
