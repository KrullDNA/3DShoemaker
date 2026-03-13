# -*- coding: utf-8 -*-
"""Establish the last baseline

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "Establish"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Establish invoked.")
    Rhino.RhinoApp.WriteLine("  Establish the last baseline")
    return 0
