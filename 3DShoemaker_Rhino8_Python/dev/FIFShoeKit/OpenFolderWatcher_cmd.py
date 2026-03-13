# -*- coding: utf-8 -*-
"""Opens folder watcher for automatic scan file import.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc
import os
import System

__commandname__ = "OpenFolderWatcher"


def RunCommand(is_interactive):
    try:
        # Prompt user for folder to watch
        dialog = Rhino.UI.OpenFileDialog()
        dialog.Title = "Select folder to watch (pick any file in target folder)"
        dialog.Filter = "All Files (*.*)|*.*"

        if not dialog.ShowOpenDialog():
            # Try using GetString as fallback
            gs = ric.GetString()
            gs.SetCommandPrompt("Enter folder path to watch")
            gs.Get()
            if gs.CommandResult() != rc.Result.Success:
                return rc.Result.Cancel
            folder_path = gs.StringResult().strip()
        else:
            folder_path = os.path.dirname(dialog.FileName)

        if not os.path.isdir(folder_path):
            Rhino.RhinoApp.WriteLine("Invalid folder path: {0}".format(folder_path))
            return rc.Result.Failure

        # Store the watch folder in sticky
        sc.sticky["FIF_WatchFolder"] = folder_path

        # Set up a file system watcher
        watcher = System.IO.FileSystemWatcher()
        watcher.Path = folder_path
        watcher.Filter = "*.*"
        watcher.NotifyFilter = (
            System.IO.NotifyFilters.FileName |
            System.IO.NotifyFilters.LastWrite
        )
        watcher.EnableRaisingEvents = True

        # Store watcher reference to keep it alive
        sc.sticky["FIF_FolderWatcher"] = watcher

        Rhino.RhinoApp.WriteLine("Folder watcher opened for: {0}".format(folder_path))
        Rhino.RhinoApp.WriteLine("Watching for new scan files...")
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error opening folder watcher: {0}".format(e))
        return rc.Result.Failure
