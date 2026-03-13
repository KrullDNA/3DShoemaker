# -*- coding: utf-8 -*-
"""Grade to multiple sizes at once

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "BatchGrade"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] BatchGrade invoked.")
    Rhino.RhinoApp.WriteLine("  Grade to multiple sizes at once")
    return 0
