"""
3DShoemaker data models package.

Provides the core data classes for footwear CAD components:
- Last: Shoe last with all geometric parameters, curves, and body surfaces
- Insert: Insole/insert with design curves, surfaces, and body geometry
- Bottom: Sole, heel, and support structures
- Foot: Human foot measurements, landmarks, and scan geometry
"""

from plugin.models.last import Last
from plugin.models.insert import Insert
from plugin.models.bottom import Bottom
from plugin.models.foot import Foot

__all__ = ["Last", "Insert", "Bottom", "Foot"]
