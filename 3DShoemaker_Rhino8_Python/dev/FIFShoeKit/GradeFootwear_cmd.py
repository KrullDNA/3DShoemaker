# -*- coding: utf-8 -*-
"""Grade footwear to a specific size

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "GradeFootwear"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] GradeFootwear invoked.")
    Rhino.RhinoApp.WriteLine("  Grade footwear to a specific size")
    return 0
