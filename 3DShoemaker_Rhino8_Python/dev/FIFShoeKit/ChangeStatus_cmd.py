# -*- coding: utf-8 -*-
"""Change the build status

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeStatus"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeStatus invoked.")
    Rhino.RhinoApp.WriteLine("  Change the build status")
    return 0
