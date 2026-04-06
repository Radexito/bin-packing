from pydantic import BaseModel
from models.product import Product


class PlacedItem(BaseModel):
    """A product placed inside a container at a specific position."""
    product: Product

    # Position inside container (mm)
    pos_x: int
    pos_y: int
    pos_z: int

    # Placed dimensions in mm (may differ from product.width/depth/height when rotated)
    placed_width: int = 0
    placed_depth: int = 0
    placed_height: int = 0

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
        """Placed width in mm."""
        return self.placed_width or self.product.width

    @property
    def rotated_depth(self) -> int:
        """Placed depth in mm."""
        return self.placed_depth or self.product.depth

    @property
    def rotated_height(self) -> int:
        """Placed height in mm."""
        return self.placed_height or self.product.height
