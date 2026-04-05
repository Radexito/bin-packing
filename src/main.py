"""Bin Packing entry point."""
import logging
import random

from models import Product
from models.container import Container
from packing import pack_products
from exporter import export_to_json
from visualizer import visualize
from enums import HazardClass

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_ALL_HAZARD_CLASSES = list(HazardClass)

def _random_hazard_classes() -> list[HazardClass]:
    """Return a random (possibly empty) subset of hazard classes."""
    k = random.randint(0, 2)
    return random.sample(_ALL_HAZARD_CLASSES, k)

def generate_products() -> list[Product]:
    """Generate a list of sample products for packing."""

    templates = [
        Product(sku="A4", name="large-box", width=500, depth=500, height=500, weight=10000, fragile=random.choice([True, False]), allow_rotations=random.choice([True, False]), hazard_classes=_random_hazard_classes()),
        Product(sku="A3", name="medium-large-box", width=350, depth=350, height=350, weight=5100, fragile=random.choice([True, False]), allow_rotations=random.choice([True, False]), hazard_classes=_random_hazard_classes()),
        Product(sku="A2", name="medium-box", width=200, depth=350, height=250, weight=5100, fragile=random.choice([True, False]), allow_rotations=random.choice([True, False]), hazard_classes=_random_hazard_classes()),
        Product(sku="A1", name="small-box", width=100, depth=300, height=200, weight=3100, fragile=random.choice([True, False]), allow_rotations=random.choice([True, False]), hazard_classes=_random_hazard_classes()),
    ]

    # create distinct instances for each copy to avoid shared-object side-effects
    products: list[Product] = []
    for i,tmpl in enumerate(templates):
        for _ in range(20*(i+1)):
            products.append(
                Product(
                    sku=tmpl.sku,
                    name=getattr(tmpl, "name", None),
                    width=tmpl.width,
                    depth=tmpl.depth,
                    height=tmpl.height,
                    weight=getattr(tmpl, "weight", 0),
                )
            )

    return products

def create_initial_pallet() -> Container:
    """Create the first pallet."""
    return Container(name="Pallet-1", width=1200, depth=800, height=1500, max_weight=1_500_000)

def main():
    # Generate products
    products = generate_products()

    # Create initial pallet
    first_pallet = create_initial_pallet()
    logger.info("Created first pallet: %s", first_pallet)

    # Pack products into pallets
    pallets = pack_products(products, first_pallet)

    # Log results of the packing process
    for pallet in pallets:
        logger.info("\n%s contains:", pallet.name)
        for item in pallet.items:
            logger.info(
                "%s at (%d,%d,%d) size (%d,%d,%d) rot (%d,%d,%d)",
                item.product.sku, item.pos_x, item.pos_y, item.pos_z,
                item.rot_x, item.rot_y, item.rot_z,
                item.rotated_width, item.rotated_depth, item.rotated_height
            )

    # Export packed pallet information to JSON
    export_to_json(pallets, "packing_result.json")

    # Visualize the packing result
    visualize()

if __name__ == "__main__":
    main()
