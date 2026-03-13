"""
document_settings.py - Per-document settings for 3DShoemaker.

Stores design parameters, user preferences, and project metadata
that are persisted inside the .3dm file via JSON serialization.
"""

import json
from typing import Any, Dict, Optional


class DocumentSettings:
    """
    Container for all per-document settings used by the 3DShoemaker plugin.

    Each open document gets its own DocumentSettings instance managed by
    PodoCADPlugIn.  The class provides ``to_dict`` / ``from_dict`` for
    JSON round-tripping and a ``Create`` factory for default values.
    """

    # ------------------------------------------------------------------
    # Default values -- centralised so Create() and from_dict() agree
    # ------------------------------------------------------------------

    _DEFAULTS: Dict[str, Any] = {
        # Project identification
        "project_name": "",
        "project_notes": "",
        "customer_name": "",

        # Units and tolerances
        "units": "Millimeters",
        "absolute_tolerance": 0.01,
        "relative_tolerance": 0.01,
        "angle_tolerance_degrees": 1.0,

        # Last parameters
        "last_size": 0.0,
        "last_size_system": "EU",       # EU, US, UK, Mondopoint
        "last_width": "",               # e.g. "D", "E", "EE"
        "last_style": "Standard",
        "last_toe_shape": "Round",
        "last_heel_height_mm": 0.0,
        "last_cone_angle_degrees": 0.0,
        "last_symmetry": "Right",       # Right, Left, Symmetric

        # Insert / insole parameters
        "insert_thickness_mm": 3.0,
        "insert_top_cover_mm": 1.0,
        "insert_bottom_cover_mm": 0.0,
        "insert_posting_medial_mm": 0.0,
        "insert_posting_lateral_mm": 0.0,
        "insert_arch_height_mm": 0.0,
        "insert_heel_cup_depth_mm": 0.0,
        "insert_material": "EVA",

        # Bottom / outsole parameters
        "bottom_thickness_mm": 4.0,
        "bottom_material": "Rubber",
        "bottom_profile": "Flat",

        # Foot scan reference
        "foot_scan_path": "",
        "foot_side": "Right",

        # Rendering / display preferences
        "show_construction_lines": True,
        "show_measurements": True,
        "display_mode": "Shaded",

        # Export preferences
        "export_format": "STL",
        "export_stl_tolerance": 0.05,
        "export_stl_angle_tolerance": 5.0,

        # Versioning -- tracks which plugin version last wrote this doc
        "saved_with_version": "",
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialise settings from keyword arguments.

        Any key not supplied falls back to the default defined in
        ``_DEFAULTS``.  Extra keys (e.g. from a future plugin version)
        are stored so they are not silently lost.
        """
        for key, default in self._DEFAULTS.items():
            setattr(self, key, kwargs.pop(key, default))

        # Preserve unknown keys for forward-compatibility
        self._extra: Dict[str, Any] = {}
        for key, value in kwargs.items():
            self._extra[key] = value

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def Create(cls, **overrides: Any) -> "DocumentSettings":
        """
        Create a new DocumentSettings populated with defaults.

        Keyword arguments override individual defaults.
        """
        return cls(**overrides)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dict of all settings (including extras)."""
        data: Dict[str, Any] = {}
        for key in self._DEFAULTS:
            data[key] = getattr(self, key, self._DEFAULTS[key])
        data.update(self._extra)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentSettings":
        """
        Re-create a DocumentSettings from a dict (e.g. loaded from JSON).

        Unknown keys are preserved internally.
        """
        if data is None:
            return cls.Create()
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        """Convenience: serialise directly to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "DocumentSettings":
        """Convenience: deserialise from a JSON string."""
        data = json.loads(raw)
        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # Accessors / mutators
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value by name, with optional default."""
        if hasattr(self, key):
            return getattr(self, key)
        return self._extra.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value by name."""
        if key in self._DEFAULTS:
            setattr(self, key, value)
        else:
            self._extra[key] = value

    def reset_to_defaults(self) -> None:
        """Restore every setting to its default value."""
        for key, default in self._DEFAULTS.items():
            setattr(self, key, default)
        self._extra.clear()

    def diff_from_defaults(self) -> Dict[str, Any]:
        """Return only the settings that differ from defaults."""
        changes: Dict[str, Any] = {}
        for key, default in self._DEFAULTS.items():
            current = getattr(self, key, default)
            if current != default:
                changes[key] = current
        changes.update(self._extra)
        return changes

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    def merge(self, other: "DocumentSettings") -> None:
        """
        Merge non-default values from *other* into this instance.

        Only settings that differ from the default in *other* overwrite
        the corresponding setting in *self*.
        """
        for key, value in other.diff_from_defaults().items():
            self.set(key, value)

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy(self) -> "DocumentSettings":
        """Return a deep copy of this settings object."""
        return DocumentSettings.from_dict(self.to_dict())

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        non_default = self.diff_from_defaults()
        if non_default:
            pairs = ", ".join(f"{k}={v!r}" for k, v in non_default.items())
            return f"<DocumentSettings {pairs}>"
        return "<DocumentSettings (defaults)>"
