# -*- coding: utf-8 -*-
"""Export the current last to file

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ExportLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ExportLast invoked.")
    Rhino.RhinoApp.WriteLine("  Export the current last to file")
    return 0
