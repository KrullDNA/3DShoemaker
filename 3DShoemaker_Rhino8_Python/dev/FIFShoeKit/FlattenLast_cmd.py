# -*- coding: utf-8 -*-
"""Flatten the last for 2D output

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "FlattenLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] FlattenLast invoked.")
    Rhino.RhinoApp.WriteLine("  Flatten the last for 2D output")
    return 0
