from datetime import datetime, timezone
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field
from enum import Enum, auto

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
    """Is product fragile."""
    flammable: bool = False
    """Is product flammable."""
    geometry_type: GeometryType = GeometryType.RECTANGLE
    """Geometry type of the product."""
    geometry_data: Optional[List[Tuple[int, int]]] = None
    """Geometry data of the product (bounding box as vectors (min, max points)."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Date and time when the container model was created."""
