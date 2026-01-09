"""Bin Packing entry point."""
import logging
from models import Product
from models.container import Container
from packing import pack_products
from exporter import export_to_json
from visualizer import visualize

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    # Create initial pallet
    first_pallet = Container(name="Pallet-1", width=1200, depth=800, height=1500, max_weight=1_500_000)
    logger.info("Created first pallet: %s", first_pallet)

    # Generate products
    products = [
        Product(sku="A1", name="small-box", width=100, depth=300, height=200, weight=3100)
        for _ in range(10)
    ] + [
        Product(sku="A2", name="medium-box", width=200, depth=350, height=250, weight=5100)
        for _ in range(10)
    ] + [
        Product(sku="A3", name="large-box", width=500, depth=500, height=500, weight=10000)
        for _ in range(10)
    ]

    # Pack products
    pallets = pack_products(products, first_pallet)

    # Log results
    for pallet in pallets:
        logger.info("\n%s contains:", pallet.name)
        for item in pallet.items:
            logger.info(
                "%s at (%d,%d,%d) size (%d,%d,%d)",
                item.product.sku, item.x, item.y, item.z, item.width, item.depth, item.height
            )

    # Export & visualize
    export_to_json(pallets, "packing_result.json")
    visualize()


if __name__ == "__main__":
    main()
