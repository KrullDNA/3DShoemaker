# -*- coding: utf-8 -*-
"""Import parameters from file

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ImportParameters"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ImportParameters invoked.")
    Rhino.RhinoApp.WriteLine("  Import parameters from file")
    return 0
