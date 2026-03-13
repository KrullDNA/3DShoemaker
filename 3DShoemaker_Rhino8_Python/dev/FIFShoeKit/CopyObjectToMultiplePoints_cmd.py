# -*- coding: utf-8 -*-
"""Copy an object to multiple locations

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CopyObjectToMultiplePoints"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CopyObjectToMultiplePoints invoked.")
    Rhino.RhinoApp.WriteLine("  Copy an object to multiple locations")
    return 0
