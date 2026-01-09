"""Product model."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


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
    awkward: bool = False
    """Is product awkward sized (irregular, non rectangular)."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """Date and time when the container model was created."""
