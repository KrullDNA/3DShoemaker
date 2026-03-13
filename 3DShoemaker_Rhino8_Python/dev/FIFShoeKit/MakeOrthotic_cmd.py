# -*- coding: utf-8 -*-
"""Create an orthotic from foot and last data

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "MakeOrthotic"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] MakeOrthotic invoked.")
    Rhino.RhinoApp.WriteLine("  Create an orthotic from foot and last data")
    return 0
