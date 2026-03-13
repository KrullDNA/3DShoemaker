# -*- coding: utf-8 -*-
"""Import a shoe last from file

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ImportLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ImportLast invoked.")
    Rhino.RhinoApp.WriteLine("  Import a shoe last from file")
    return 0
