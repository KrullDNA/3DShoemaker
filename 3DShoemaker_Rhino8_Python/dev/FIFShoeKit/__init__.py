"""
Feet in Focus Shoe Kit - Rhino 8 Python Plugin Entry Point.

This module is the entry point that Rhino 8 loads when the plugin is
installed into the PythonPlugIns directory.  Rhino discovers this file
via the ``manifest.yml`` sitting alongside it and calls the module-level
code to register commands and initialize the plugin.

Directory layout when installed::

    PythonPlugIns/
      FIFShoeKit/
        __init__.py          <-- this file
        manifest.yml
        Terms.txt
        plugin/
          __init__.py
          plugin_main.py
          document_settings.py
          material_thicknesses.py
          preview_module.py
          commands/
            __init__.py
            last_commands.py
            morph_commands.py
            component_commands.py
            grade_commands.py
          forms/
            __init__.py
            ...
          utils/
            __init__.py
            geometry_utils.py
            json_serializer.py
            layer_manager.py
            snap_curves.py
            squeeze.py
"""

import os
import sys
import traceback

# ---------------------------------------------------------------------------
# Ensure our plugin package is importable.
#
# When Rhino loads a PythonPlugIn it sets the working directory to the
# plugin folder.  We add that folder to sys.path so that
# ``import plugin`` resolves to our ``plugin/`` sub-package.
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


# ---------------------------------------------------------------------------
# Import Rhino namespaces (available at runtime inside Rhino 8)
# ---------------------------------------------------------------------------

import Rhino  # type: ignore
import Rhino.Commands  # type: ignore
import Rhino.Plugins  # type: ignore
import Rhino.RhinoApp  # type: ignore


# ---------------------------------------------------------------------------
# Import plugin internals
# ---------------------------------------------------------------------------

try:
    import plugin as plugin_pkg
    from plugin.plugin_main import PodoCADPlugIn

    # Import all command modules -- this registers the command classes
    from plugin.commands import (
        # Last
        NewBuild,
        NewBuildScriptable,
        UpdateLast,
        ImportLast,
        ExportLast,
        GradeLast,
        FlattenLast,
        GazeAtLast,
        ChangeLastParameterization,
        ExportLastParameters,
        ImportParameters,
        ExportMeasurementEquations,
        NameObjectsInDoc,
        GetObjectIDName,
        Establish,
        # Morph
        Morph,
        NewMorph,
        NewMorphScriptable,
        # Components
        CreateInsole,
        CreateSole,
        CreateHeel,
        CreateHeelParts,
        CreateTopPiece,
        CreateShankBoard,
        CreateMetPad,
        CreateToeCrest,
        CreateToeRidge,
        CreateThongHole,
        CreatePinHole,
        CreateShoeTree,
        CreateUpperBodies,
        MakeComponent,
        CreateAlphaJoint,
        CreateRailGuideJoint,
        CreateMockup,
    )

    # Import utility modules (makes them available for commands)
    from plugin.utils import (
        GeometryUtils,
        JsonSerializer,
        LayerManager,
        SnapCurves,
        Squeeze,
    )

    _IMPORTS_OK = True

except Exception as _import_err:
    _IMPORTS_OK = False
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Import error: {0}\n{1}".format(
            _import_err, traceback.format_exc()
        )
    )


# ---------------------------------------------------------------------------
# All command classes that Rhino should discover.
#
# Rhino 8 Python plugins expose commands by listing them at module level.
# Each class must derive from Rhino.Commands.Command and implement
# ``EnglishName`` and ``RunCommand``.
# ---------------------------------------------------------------------------

if _IMPORTS_OK:
    _ALL_COMMANDS = [
        # Last
        NewBuild,
        NewBuildScriptable,
        UpdateLast,
        ImportLast,
        ExportLast,
        GradeLast,
        FlattenLast,
        GazeAtLast,
        ChangeLastParameterization,
        ExportLastParameters,
        ImportParameters,
        ExportMeasurementEquations,
        NameObjectsInDoc,
        GetObjectIDName,
        Establish,
        # Morph
        Morph,
        NewMorph,
        NewMorphScriptable,
        # Components
        CreateInsole,
        CreateSole,
        CreateHeel,
        CreateHeelParts,
        CreateTopPiece,
        CreateShankBoard,
        CreateMetPad,
        CreateToeCrest,
        CreateToeRidge,
        CreateThongHole,
        CreatePinHole,
        CreateShoeTree,
        CreateUpperBodies,
        MakeComponent,
        CreateAlphaJoint,
        CreateRailGuideJoint,
        CreateMockup,
    ]
else:
    _ALL_COMMANDS = []


# ---------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def _initialize_plugin():
    """Initialize the Feet in Focus Shoe Kit plugin singleton and wire it into Rhino."""
    if not _IMPORTS_OK:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Skipping initialization due to import errors."
        )
        return

    try:
        instance = PodoCADPlugIn.instance()
        success = instance.Initialize()
        if success:
            Rhino.RhinoApp.WriteLine(
                "[Feet in Focus Shoe Kit] Plugin loaded: "
                "v{0}, {1} commands registered.".format(
                    plugin_pkg.__version__, len(_ALL_COMMANDS)
                )
            )
        else:
            Rhino.RhinoApp.WriteLine(
                "[Feet in Focus Shoe Kit] Plugin initialization returned False. "
                "Some features may be unavailable."
            )
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Initialization failed: {0}\n{1}".format(
                ex, traceback.format_exc()
            )
        )


# Run initialization when this module is first imported by Rhino
_initialize_plugin()
