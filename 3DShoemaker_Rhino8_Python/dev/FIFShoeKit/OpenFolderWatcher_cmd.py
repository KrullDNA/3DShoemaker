# -*- coding: utf-8 -*-
"""Open the folder watcher utility

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "OpenFolderWatcher"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] OpenFolderWatcher invoked.")
    Rhino.RhinoApp.WriteLine("  Open the folder watcher utility")
    return 0
