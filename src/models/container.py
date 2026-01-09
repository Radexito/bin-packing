"""Container model."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, root_validator

from models.placed_item import PlacedItem


class Container(BaseModel):
    """Dataclass for container model."""
    id: Optional[int] = None
    """Unique ID of the container."""
    name: str
    """Name of the container model."""
    width: int
    """Width of the container model in mm."""
    depth: int
    """Depth of the container model in mm."""
    height: int
    """Height of the container model in mm."""
    max_weight: int
    """Maximum weight of the container model in grams."""
    created_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc))
    """Date and time when the container model was created."""
    items: list[PlacedItem] = Field(default_factory=list)
    """List of products in this container.."""
    spaces: list[tuple[int,int,int,int,int,int]] = Field(default_factory=list)
    """List of spaces in this container."""

    def model_post_init(self, __context=None):
        if not self.spaces:
            self.spaces.append((0, 0, 0, self.width, self.depth, self.height))