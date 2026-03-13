# -*- coding: utf-8 -*-
"""Add a metatarsal pad

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateMetPad"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateMetPad invoked.")
    Rhino.RhinoApp.WriteLine("  Add a metatarsal pad")
    return 0
