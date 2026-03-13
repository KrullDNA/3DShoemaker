# -*- coding: utf-8 -*-
"""Prepare model for 3D printing

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "PrintPrep"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] PrintPrep invoked.")
    Rhino.RhinoApp.WriteLine("  Prepare model for 3D printing")
    return 0
