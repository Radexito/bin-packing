"""Packing logic: place products in containers."""
from typing import List
import logging

from models.product import Product
from models.container import Container
from models.placed_item import PlacedItem

logger = logging.getLogger(__name__)

def pack_products(products: List[Product], first_pallet: Container) -> List[Container]:
    """Pack a list of products into containers."""
    pallets = [first_pallet]
    products_to_place = products.copy()
    pallet_index = 1

    while products_to_place:
        pallet = pallets[-1]
        remaining: List[Product] = []
        any_placed = False

        for product in products_to_place:
            if place_product(pallet, product):
                any_placed = True
            else:
                remaining.append(product)

        if not any_placed:
            pallet_index += 1
            new_pallet = Container(
                name=f"Pallet-{pallet_index}",
                width=first_pallet.width,
                depth=first_pallet.depth,
                height=first_pallet.height,
                max_weight=first_pallet.max_weight,
            )
            pallets.append(new_pallet)

        products_to_place = remaining

    return pallets

def place_product(container: Container, product: Product) -> bool:
    """Try to place a product into a container using guillotine packing."""
    for i, (x, y, z, w, d, h) in enumerate(container.spaces):
        rotations = [(product.width, product.depth, product.height)]
        if product.allow_rotations:
            rotations += [
                (product.width, product.height, product.depth),
                (product.depth, product.width, product.height),
                (product.depth, product.height, product.width),
                (product.height, product.width, product.depth),
                (product.height, product.depth, product.width),
            ]

        for rw, rd, rh in rotations:
            if rw > w or rd > d or rh > h:
                continue

            total_weight = sum(item.product.weight for item in container.items) + product.weight
            if total_weight > container.max_weight:
                continue

            placed = PlacedItem(
                product=product,
                pos_x=x,
                pos_y=y,
                pos_z=z,
                rot_x=0,  # Rotation not applied yet (you can modify as needed)
                rot_y=0,
                rot_z=0,
            )
            container.items.append(placed)

            logger.debug(
                "Placed %s at (%d,%d,%d) size (%d,%d,%d)",
                product.sku, x, y, z, rw, rd, rh
            )

            # Remove used space and split
            container.spaces.pop(i)
            if w - rw > 0:
                container.spaces.append((x + rw, y, z, w - rw, rd, rh))
            if d - rd > 0:
                container.spaces.append((x, y + rd, z, rw, d - rd, rh))
            if h - rh > 0:
                container.spaces.append((x, y, z + rh, rw, rd, h - rh))

            return True

    return False
