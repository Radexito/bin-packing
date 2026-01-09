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

def _boxes_intersect(a_pos, a_size, b_pos, b_size) -> bool:
    """Axis-aligned bounding-box intersection test."""
    ax1, ay1, az1 = a_pos
    aw, ad, ah = a_size
    ax2, ay2, az2 = ax1 + aw, ay1 + ad, az1 + ah

    bx1, by1, bz1 = b_pos
    bw, bd, bh = b_size
    bx2, by2, bz2 = bx1 + bw, by1 + bd, bz1 + bh

    # overlap in all three axes means intersection
    return not (ax2 <= bx1 or ax1 >= bx2 or ay2 <= by1 or ay1 >= by2 or az2 <= bz1 or az1 >= bz2)

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

            # Ensure placement stays within the container's global bounds (also disallow negative positions)
            if x < 0 or y < 0 or z < 0 or x + rw > container.width or y + rd > container.depth or z + rh > container.height:
                logger.debug("Skipping %s rotation (%s,%s,%s): out of container bounds at (%s,%s,%s)",
                             product.sku, rw, rd, rh, x, y, z)
                continue

            # Weight check
            total_weight = sum(item.product.weight for item in container.items) + product.weight
            if total_weight > container.max_weight:
                continue

            # Collision check vs already placed items — use stored placed sizes if present
            collision = False
            for existing in container.items:
                existing_pos = (existing.pos_x, existing.pos_y, existing.pos_z)
                ew = getattr(existing, "rot_x", None)
                ed = getattr(existing, "rot_y", None)
                eh = getattr(existing, "rot_z", None)
                # use explicit None checks (avoid treating 0 as missing)
                if ew is None or ed is None or eh is None:
                    existing_size = (existing.product.width, existing.product.depth, existing.product.height)
                else:
                    existing_size = (ew, ed, eh)
                if _boxes_intersect((x, y, z), (rw, rd, rh), existing_pos, existing_size):
                    collision = True
                    break
            if collision:
                logger.debug("Skipping %s at (%s,%s,%s) size (%s,%s,%s): collision", product.sku, x, y, z, rw, rd, rh)
                continue

            # create a lightweight Product instance reflecting the placed (rotated) dimensions
            try:
                rotated_product = Product(
                    sku=product.sku,
                    name=getattr(product, "name", None),
                    width=rw,
                    depth=rd,
                    height=rh,
                    weight=getattr(product, "weight", 0),
                )
            except Exception:
                # fallback: if Product signature differs, keep original product but also attach rotated attrs to the placed item below
                rotated_product = product

            placed = PlacedItem(
                product=rotated_product,
                pos_x=x,
                pos_y=y,
                pos_z=z,
                rot_x=rw,  # store placed dimensions in rot_* fields so future checks use them
                rot_y=rd,
                rot_z=rh,
            )

            container.items.append(placed)

            logger.debug(
                "Placed %s at (%s,%s,%s) size (%s,%s,%s)",
                product.sku, x, y, z, rw, rd, rh
            )

            # Remove used space and split — clamp created spaces to container bounds
            container.spaces.pop(i)

            # Right slice (along X): remaining width, full original depth & height
            nx, ny, nz = x + rw, y, z
            nw = w - rw
            if nw > 0:
                # clamp to container bounds
                nw = min(nw, max(0, container.width - nx))
                if nw > 0 and nx < container.width:
                    container.spaces.append((nx, ny, nz, nw, d, h))

            # Front slice (along Y): width limited to placed width, remaining depth
            fx, fy, fz = x, y + rd, z
            fw = rw
            fd = d - rd
            if fd > 0 and fw > 0:
                fw = min(fw, max(0, container.width - fx))
                fd = min(fd, max(0, container.depth - fy))
                if fw > 0 and fd > 0 and fx < container.width and fy < container.depth:
                    container.spaces.append((fx, fy, fz, fw, fd, h))

            # Top slice (along Z): width = placed width, depth = placed depth, remaining height
            tx, ty, tz = x, y, z + rh
            tw, td, th = rw, rd, h - rh
            if th > 0 and tw > 0 and td > 0:
                tw = min(tw, max(0, container.width - tx))
                td = min(td, max(0, container.depth - ty))
                th = min(th, max(0, container.height - tz))
                if tw > 0 and td > 0 and th > 0 and tx < container.width and ty < container.depth and tz < container.height:
                    container.spaces.append((tx, ty, tz, tw, td, th))

            return True

    return False
