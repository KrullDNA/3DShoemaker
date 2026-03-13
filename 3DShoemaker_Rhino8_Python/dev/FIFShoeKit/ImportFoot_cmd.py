# -*- coding: utf-8 -*-
"""Import a foot scan or model

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ImportFoot"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ImportFoot invoked.")
    Rhino.RhinoApp.WriteLine("  Import a foot scan or model")
    return 0
