from pydantic import BaseModel
from models.product import Product

class PlacedItem(BaseModel):
    """A product placed inside a container at a specific position and rotation."""
    product: Product

    # Position inside container (mm)
    pos_x: int
    pos_y: int
    pos_z: int

    # Rotation in degrees
    rot_x: int = 0
    rot_y: int = 0
    rot_z: int = 0

    @property
    def weight(self) -> int:
        return self.product.weight

    @property
    def sku(self) -> str:
        return self.product.sku

    @property
    def name(self) -> str | None:
        return self.product.name

    @property
    def rotated_width(self) -> int:
        """Return the width after applying rotations."""
        if self.rot_x == 90 or self.rot_x == 270:
            return self.product.depth
        return self.product.width

    @property
    def rotated_depth(self) -> int:
        """Return the depth after applying rotations."""
        if self.rot_x == 90 or self.rot_x == 270:
            return self.product.width
        return self.product.depth

    @property
    def rotated_height(self) -> int:
        """Return the height of the placed item."""
        return self.product.height
