# -*- coding: utf-8 -*-
"""Add a metatarsal pad to sandal

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AddMetpad"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AddMetpad invoked.")
    Rhino.RhinoApp.WriteLine("  Add a metatarsal pad to sandal")
    return 0
