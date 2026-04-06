"""Bin Packing entry point."""
import logging
import random

from models import Product
from models.container import Container
from packing import pack_products
from exporter import export_to_json
from visualizer import visualize
from enums import GeometryType, HazardClass, OrientationConstraint

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_ALL_HAZARD_CLASSES = list(HazardClass)
_CONSTRAINTS = [None, None, None, OrientationConstraint.UPRIGHT_ONLY, OrientationConstraint.NO_LAY_FLAT]


def _random_hazard_classes() -> list[HazardClass]:
    """Return a random (possibly empty) subset of hazard classes."""
    k = random.randint(0, 2)
    return random.sample(_ALL_HAZARD_CLASSES, k)


def generate_products() -> list[Product]:
    """Generate a list of sample products for packing."""
    templates = [
        Product(sku="A4", name="large-box",        width=500, depth=500, height=500, weight=10000),
        Product(sku="A3", name="medium-large-box",  width=350, depth=350, height=350, weight=5100),
        Product(sku="A2", name="medium-box",         width=200, depth=350, height=250, weight=5100),
        Product(sku="A1", name="small-box",          width=100, depth=300, height=200, weight=3100),
        # Non-rectangular: right-angled triangle with legs 300×200 mm
        Product(
            sku="TRI", name="triangle-box",
            width=300, depth=200, height=150, weight=2000,
            geometry_type=GeometryType.TRIANGLE,
            geometry_data=[(0, 0), (300, 0), (0, 200)],
            orientation_constraints=OrientationConstraint.NO_LAY_FLAT,
        ),
    ]

    products: list[Product] = []
    for i, tmpl in enumerate(templates[:4]):
        for _ in range(20*(i+1)):
            products.append(tmpl.model_copy(update={
                "fragile": random.choice([True, False]),
                "hazard_classes": _random_hazard_classes(),
                "stackable": random.choices([True, False], weights=[9, 1])[0],
                "orientation_constraints": random.choice(_CONSTRAINTS),
            }))

    # Add 10 triangle items for geometry testing
    tri_tmpl = templates[4]
    for _ in range(10):
        products.append(tri_tmpl.model_copy(update={
            "fragile": random.choice([True, False]),
            "hazard_classes": _random_hazard_classes(),
        }))

    return products


def create_initial_pallet() -> Container:
    """Create the first pallet."""
    return Container(name="Pallet-1", width=1200, depth=800, height=1500, max_weight=1_500_000)


def main():
    products = generate_products()
    first_pallet = create_initial_pallet()
    logger.info("Created first pallet: %s", first_pallet)

    pallets = pack_products(products, first_pallet)

    for pallet in pallets:
        logger.info("\n%s contains:", pallet.name)
        for item in pallet.items:
            logger.info(
                "%s at (%d,%d,%d) placed (%d,%d,%d)",
                item.product.sku, item.pos_x, item.pos_y, item.pos_z,
                item.rotated_width, item.rotated_depth, item.rotated_height
            )

    export_to_json(pallets, "packing_result.json")
    visualize()


if __name__ == "__main__":
    main()
