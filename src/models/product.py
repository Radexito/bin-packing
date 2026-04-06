from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum, auto

from enums import HazardClass, OrientationConstraint


class GeometryType(str, Enum):
    RECTANGLE = "RECTANGLE"
    TRIANGLE  = "TRIANGLE"
    POLYGON   = "POLYGON"
    CUSTOM    = "CUSTOM"


class Product(BaseModel):
    """Dataclass for product model."""
    id: Optional[int] = None
    sku: str
    name: Optional[str] = None
    width: int
    depth: int
    height: int
    weight: int
    orientation_constraints: Optional[OrientationConstraint] = None
    """Allowed orientations during packing.
    None (default): all 6 rotations permitted.
    UPRIGHT_ONLY: no rotation — placed exactly as defined.
    NO_LAY_FLAT: Z-axis only — width/depth may swap, height stays height."""
    fragile: bool = False
    stackable: bool = True
    """Whether other items may be placed on top of this product."""
    hazard_classes: List[HazardClass] = Field(default_factory=list)
    """UN Dangerous Goods hazard classes. Replaces the former `flammable` boolean."""
    geometry_type: GeometryType = GeometryType.RECTANGLE
    geometry_data: Optional[List[Tuple[int, int]]] = None
    """2D polygon vertices describing the footprint in mm, relative to item corner (0,0).
    Format: [(x0,y0), (x1,y1), ...] — closed polygon, first ≠ last point.
    Used for TRIANGLE and POLYGON geometry types; ignored for RECTANGLE and CUSTOM.
    The packer derives the axis-aligned bounding box from these vertices."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_flammable(self) -> bool:
        return any(hc.is_flammable for hc in self.hazard_classes)

    @property
    def requires_segregation(self) -> bool:
        return any(hc.requires_segregation for hc in self.hazard_classes)
