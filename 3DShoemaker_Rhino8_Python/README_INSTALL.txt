========================================================
  FEET IN FOCUS SHOE KIT v1.0 - Installation & Quick Start
  Professional Footwear Design Plugin for Rhino 8
========================================================


SYSTEM REQUIREMENTS
-------------------
- Rhinoceros 3D version 8.0 or later (Windows or macOS)
- No additional software, compilers, or SDKs required
- Recommended: 8 GB RAM, dedicated GPU for viewport


INSTALLATION
------------
1. Close Rhino 8 if it is currently running.

2. Locate the file:  FIFShoeKit_1.0.rhi
   (This is the installer file you received.)

3. Double-click the .rhi file.
   The Rhino Package Installer will open automatically.

4. Click "Install" when prompted.
   You should see a confirmation message that the plugin
   was installed successfully.

5. Open Rhino 8.
   The plugin loads automatically on startup.
   You should see "[Feet in Focus Shoe Kit] Plugin loaded"
   in the command history.


USING THE TOOLBAR
-----------------
1. In Rhino, go to:
      View  >  Toolbars

2. Find "Feet in Focus Shoe Kit" in the toolbar list and
   enable it.

3. The toolbar contains command buttons arranged in
   seven groups:
   - Last:        New Build, Import Last, Export Last,
                  Update Last, Grade Last, Flatten Last
   - Morph:       Morph, New Morph
   - Components:  Create Insole, Create Sole, Create Heel,
                  Create Top Piece, Create Shank Board
   - Foot:        Import Foot, Analyze Plantar Foot Scan
   - Orthotic:    Make Orthotic, Adjust Orthotic To Blank,
                  Print Prep Orthotic
   - Sandal:      Build Sandal, Build Insert
   - Utility:     Grade Footwear, Print Prep, Export


QUICK START WORKFLOW - SHOE LAST DESIGN
---------------------------------------
Follow these steps to begin a footwear design:

 1. NEW BUILD
    Click "NewBuild" or type NewBuild in the command line.
    This creates a new shoe last build with default
    parameters. Use "NewBuildScriptable" for automated
    builds with pre-set parameters.

 2. IMPORT LAST
    Click "ImportLast" to import an existing shoe last
    from a 3DM, STEP, or IGES file. The last will be
    loaded and parameterized for editing.

 3. MORPH
    Use "Morph" or "NewMorph" to morph the last shape.
    Adjust the last geometry interactively with control
    points or use "NewMorphScriptable" for batch morphing.

 4. CREATE COMPONENTS
    Build footwear components on the last:
    - "CreateInsole" - Generate an insole from the last
    - "CreateSole" - Create the outsole
    - "CreateHeel" - Create the heel
    - "CreateTopPiece" - Create the top piece
    - "CreateShankBoard" - Create the shank board
    - "CreateMetPad" - Add a metatarsal pad
    - "CreateUpperBodies" - Generate upper pattern bodies

 5. ADJUST PARAMETERS
    Fine-tune your design:
    - "ChangeParameter" - Modify individual parameters
    - "AdjustMaterial" - Set material properties
    - "AdjustMaterialThicknesses" - Set layer thicknesses
    - "AdjustFitCustomization" - Customize fit

 6. GRADE
    Size the design up or down:
    - "GradeFootwear" - Grade to a specific size
    - "BatchGrade" - Grade to multiple sizes at once

 7. EXPORT
    Prepare for manufacturing:
    - "ExportLast" - Export the finished last
    - "PrintPrep" - Prepare for 3D printing
    - "RenderComponents" - Render component views


QUICK START WORKFLOW - ORTHOTIC DESIGN
--------------------------------------
The plugin includes integrated orthotic design commands:

 1. MAKE ORTHOTIC
    Type "MakeOrthotic" in the command line.
    Creates an orthotic device from foot and last data.

 2. ADJUST TO BLANK
    Use "AdjustOrthoticToBlank" to fit the orthotic
    design to a specific manufacturing blank.

 3. ADJUST FEATURES
    - "AdjustOrthoticArchHeightAndLength" - Modify arch
    - "AdjustOrthoticFeature" - Adjust posting, met pad,
      heel lift, and other features
    - "TwistOrthotic" - Apply twist deformation

 4. PRINT PREP
    - "PrintPrepOrthotic" - Prepare a single orthotic
      for 3D printing
    - "PrintPrepOrthotics" - Batch prepare multiple
      orthotics for 3D printing


QUICK START WORKFLOW - SANDAL DESIGN
-------------------------------------
Design sandals and custom inserts:

 1. BUILD SANDAL
    Type "BuildSandal" to create a sandal from a last.

 2. BUILD INSERT
    Use "BuildInsert" to create a removable insert.

 3. ADD FEATURES
    - "AddSandalGroove" - Add a groove to the sandal
    - "AddThongSlot" - Add a thong/flip-flop slot
    - "AddMetpad" - Add a metatarsal pad


VERIFYING THE INSTALLATION
---------------------------
1. Open Rhino 8 after installation.
   You should see in the command history:
   "[Feet in Focus Shoe Kit] Plugin loaded"

2. Type  NewBuild  in the Rhino command line and
   press Enter.
   The New Build dialog should appear.

3. Check View > Toolbars for "Feet in Focus Shoe Kit".

If all of these work, the installation is successful.


TROUBLESHOOTING
---------------
Problem:  Commands are not recognized (e.g., "Unknown
          command: NewBuild").
Solution: Go to Tools > Options > Plug-ins. Look for
          "Feet in Focus Shoe Kit" in the list. Make sure
          it is enabled. Restart Rhino.

Problem:  The .rhi file does not open when double-clicked.
Solution: Right-click the file > Open With > and select
          Rhino. If Rhino is not listed, open Rhino first,
          then drag and drop the .rhi file onto the Rhino
          window.

Problem:  Plugin loads but some commands fail.
Solution: Check the Rhino command history for error
          messages. Ensure you are running Rhino 8.0 or
          later. Try restarting Rhino.

Problem:  Import/Export dialogs do not appear.
Solution: Check that your Rhino 8 installation includes
          the Python scripting component. Go to
          Tools > Options > Plug-ins and verify that
          "IronPython" or "Python 3" is enabled.

Problem:  Grading produces unexpected results.
Solution: Ensure the base last is fully parameterized
          before grading. Run "ChangeLastParameterization"
          to verify all parameters are set correctly.


MANUAL INSTALLATION (ALTERNATIVE)
----------------------------------
If double-clicking the .rhi file does not work, you can
install manually using the included install.py script:

1. Open a terminal or command prompt.

2. Navigate to the plugin directory:
      cd path/to/3DShoemaker_Rhino8_Python

3. Run the installer:
      python install.py

4. To uninstall:
      python install.py --uninstall


CONTACT / SUPPORT
-----------------
If you encounter any issues not covered above, please
contact your plugin provider or submit a support request
with the following information:

  - Rhino version (Help > About Rhinoceros)
  - Operating system and version
  - The command history output (copy from the command line)
  - A screenshot of any error message or dialog
  - Steps to reproduce the problem

Website: https://ShoeLastMaker.com

========================================================
