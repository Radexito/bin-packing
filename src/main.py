"""Bin Packing entry point."""
import logging
from models import Product
from models.container import Container
from packing import pack_products
from exporter import export_to_json
from visualizer import visualize

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_products() -> list[Product]:
    """Generate a list of sample products for packing."""
    products = [
        Product(sku="A1", name="small-box", width=100, depth=300, height=200, weight=3100),
        Product(sku="A2", name="medium-box", width=200, depth=350, height=250, weight=5100),
        Product(sku="A3", name="large-box", width=500, depth=500, height=500, weight=10000),
    ]

    # Generate 10 of each product type
    return products * 10

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
                "%s at (%d,%d,%d) size (%d,%d,%d)",
                item.product.sku, item.pos_x, item.pos_y, item.pos_z,
                item.rotated_width, item.rotated_depth, item.rotated_height
            )

    # Export packed pallet information to JSON
    export_to_json(pallets, "packing_result.json")

    # Visualize the packing result
    visualize()

if __name__ == "__main__":
    main()
