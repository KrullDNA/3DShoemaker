# -*- coding: utf-8 -*-
"""Rebuild all footwear components

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "RebuildFootwear"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] RebuildFootwear invoked.")
    Rhino.RhinoApp.WriteLine("  Rebuild all footwear components")
    return 0
