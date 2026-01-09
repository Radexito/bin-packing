"""PlacedItem model."""
from pydantic import BaseModel
from models.product import Product


class PlacedItem(BaseModel):
    """A product placed inside a container at a specific position."""
    product: Product

    # position inside container (mm)
    x: int
    y: int
    z: int

    # orientation actually used (mm)
    width: int
    depth: int
    height: int

    @property
    def weight(self) -> int:
        return self.product.weight

    @property
    def sku(self) -> str:
        return self.product.sku

    @property
    def name(self) -> str | None:
        return self.product.name
