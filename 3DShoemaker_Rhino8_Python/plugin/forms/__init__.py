"""
3DShoemaker Rhino 8 Plugin - UI Forms package.

All Eto.Forms-based dialogs and panels for the 3DShoemaker
footwear-design plugin.
"""

from plugin.forms.morph_form import MorphForm
from plugin.forms.grade_footwear_form import GradeFootwearForm
from plugin.forms.import_foot_form import ImportFootForm
from plugin.forms.foot_measurement_form import FootMeasurementForm
from plugin.forms.edit_dimension_form import EditDimensionForm
from plugin.forms.print_prep_form import PrintPrepForm
from plugin.forms.options_form import OptionsForm
from plugin.forms.terms_dialog import TermsDialog
from plugin.forms.vacuum_form import VacuumForm
from plugin.forms.podoCAD_panel import PodoCADPanel
from plugin.forms.folder_watcher import FolderWatcher

__all__ = [
    "MorphForm",
    "GradeFootwearForm",
    "ImportFootForm",
    "FootMeasurementForm",
    "EditDimensionForm",
    "PrintPrepForm",
    "OptionsForm",
    "TermsDialog",
    "VacuumForm",
    "PodoCADPanel",
    "FolderWatcher",
]
