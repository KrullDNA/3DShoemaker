"""
material_thicknesses.py - Material thickness parameters for 3DShoemaker.

Stores thickness values for every material layer in a shoe last / insole
build-up.  Persisted per-document as JSON.
"""

import json
from typing import Any, Dict, Optional


class MaterialThicknesses:
    """
    Container for material-layer thicknesses (in mm) used throughout
    the 3DShoemaker workflow.

    Instances are per-document and serialised into the .3dm user text
    alongside DocumentSettings.
    """

    # ------------------------------------------------------------------
    # Default thickness values (mm)
    # ------------------------------------------------------------------

    _DEFAULTS: Dict[str, float] = {
        # Insole / insert layers
        "insole_base": 3.0,
        "insole_top_cover": 1.0,
        "insole_bottom_cover": 0.0,
        "insole_posting_medial": 0.0,
        "insole_posting_lateral": 0.0,
        "insole_arch_fill": 0.0,
        "insole_heel_pad": 0.0,
        "insole_met_pad": 0.0,
        "insole_forefoot_extension": 0.0,
        "insole_rearfoot_extension": 0.0,

        # Last modification offsets
        "last_shell_wall": 2.0,
        "last_toe_cap": 1.5,
        "last_heel_counter": 1.5,
        "last_lining": 1.0,

        # Bottom / outsole layers
        "bottom_outsole": 4.0,
        "bottom_midsole": 6.0,
        "bottom_insole_board": 2.0,
        "bottom_shank": 1.0,
        "bottom_welt": 0.0,

        # Additions / wedges
        "medial_wedge": 0.0,
        "lateral_wedge": 0.0,
        "heel_lift": 0.0,
        "forefoot_rocker": 0.0,
        "toe_spring": 0.0,
    }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, **kwargs: Any) -> None:
        for key, default in self._DEFAULTS.items():
            setattr(self, key, float(kwargs.pop(key, default)))

        # Preserve unknown keys for forward-compatibility
        self._extra: Dict[str, float] = {}
        for key, value in kwargs.items():
            try:
                self._extra[key] = float(value)
            except (TypeError, ValueError):
                self._extra[key] = 0.0

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def Create(cls, **overrides: Any) -> "MaterialThicknesses":
        """Return a new instance with default values, optionally overridden."""
        return cls(**overrides)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, float]:
        data: Dict[str, float] = {}
        for key in self._DEFAULTS:
            data[key] = getattr(self, key, self._DEFAULTS[key])
        data.update(self._extra)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialThicknesses":
        if data is None:
            return cls()
        return cls(**data)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "MaterialThicknesses":
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, key: str, default: float = 0.0) -> float:
        """Return thickness for *key*, falling back to *default*."""
        if hasattr(self, key) and key in self._DEFAULTS:
            return getattr(self, key)
        return self._extra.get(key, default)

    def set(self, key: str, value: float) -> None:
        """Set thickness for *key*."""
        value = float(value)
        if key in self._DEFAULTS:
            setattr(self, key, value)
        else:
            self._extra[key] = value

    # ------------------------------------------------------------------
    # Aggregate helpers
    # ------------------------------------------------------------------

    def total_insole_thickness(self) -> float:
        """Sum of all insole-related layers."""
        return (
            self.insole_base
            + self.insole_top_cover
            + self.insole_bottom_cover
            + self.insole_posting_medial
            + self.insole_posting_lateral
            + self.insole_arch_fill
            + self.insole_heel_pad
            + self.insole_met_pad
            + self.insole_forefoot_extension
            + self.insole_rearfoot_extension
        )

    def total_bottom_thickness(self) -> float:
        """Sum of all bottom / outsole layers."""
        return (
            self.bottom_outsole
            + self.bottom_midsole
            + self.bottom_insole_board
            + self.bottom_shank
            + self.bottom_welt
        )

    def total_last_allowance(self) -> float:
        """Sum of last modification offsets."""
        return (
            self.last_shell_wall
            + self.last_toe_cap
            + self.last_heel_counter
            + self.last_lining
        )

    def total_build_height(self) -> float:
        """Total build-up height (insole + bottom + heel lift)."""
        return (
            self.total_insole_thickness()
            + self.total_bottom_thickness()
            + self.heel_lift
        )

    # ------------------------------------------------------------------
    # Diff / reset
    # ------------------------------------------------------------------

    def diff_from_defaults(self) -> Dict[str, float]:
        changes: Dict[str, float] = {}
        for key, default in self._DEFAULTS.items():
            current = getattr(self, key, default)
            if abs(current - default) > 1e-9:
                changes[key] = current
        changes.update(self._extra)
        return changes

    def reset_to_defaults(self) -> None:
        for key, default in self._DEFAULTS.items():
            setattr(self, key, default)
        self._extra.clear()

    def copy(self) -> "MaterialThicknesses":
        return MaterialThicknesses.from_dict(self.to_dict())

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        changed = self.diff_from_defaults()
        if changed:
            pairs = ", ".join(f"{k}={v:.2f}" for k, v in changed.items())
            return f"<MaterialThicknesses {pairs}>"
        return "<MaterialThicknesses (defaults)>"
