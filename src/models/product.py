from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum, auto

from enums import HazardClass


class GeometryType(Enum):
    RECTANGLE = auto()
    TRIANGLE = auto()
    POLYGON = auto()
    CUSTOM = auto()


class Product(BaseModel):
    """Dataclass for product model."""
    id: Optional[int] = None
    """Unique ID of the product."""
    sku: str
    """SKU of the product."""
    name: Optional[str] = None
    """Name of the product."""
    width: int
    """Width of the product in mm."""
    depth: int
    """Depth of the product in mm."""
    height: int
    """Height of the product in mm."""
    weight: int
    """Weight of the product in grams."""
    allow_rotations: bool = True
    """Allow rotations of the product."""
    orientation_constraints: Optional[str] = None
    """Orientation constraints of the product."""
    fragile: bool = False
    """Is product fragile (handling attribute — keep upright, no heavy load on top)."""
    stackable: bool = True
    """Whether other items may be placed on top of this product.
    When False, the item's full XY footprint is blocked above it."""
    hazard_classes: List[HazardClass] = Field(default_factory=list)
    """UN Dangerous Goods hazard classes assigned to this product.
    A product may carry multiple classes (e.g. toxic + corrosive).
    Replaces the former `flammable` boolean — use CLASS_3 or CLASS_4_* instead."""
    geometry_type: GeometryType = GeometryType.RECTANGLE
    """Geometry type of the product."""
    geometry_data: Optional[List[Tuple[int, int]]] = None
    """Geometry data of the product (bounding box as vectors (min, max points)."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Date and time when the container model was created."""

    @property
    def is_flammable(self) -> bool:
        """True if any assigned hazard class is flammable by UN definition."""
        return any(hc.is_flammable for hc in self.hazard_classes)

    @property
    def requires_segregation(self) -> bool:
        """True if any hazard class requires segregation from incompatible goods."""
        return any(hc.requires_segregation for hc in self.hazard_classes)
