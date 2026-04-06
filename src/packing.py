"""Packing logic: place products in containers."""
from typing import List, Optional
import logging
import uuid

from models.product import Product
from models.container import Container
from models.placed_item import PlacedItem
from enums import GeometryType

logger = logging.getLogger(__name__)

# Minimum distance from container wall for flammable items (best-effort).
FLAMMABLE_EDGE_MARGIN = 50  # mm


# ---------------------------------------------------------------------------
# Geometry helpers (issue #4)
# ---------------------------------------------------------------------------

def _bounding_box(product: Product) -> tuple[int, int, int]:
    """Return the (width, depth, height) bounding box for a product.

    RECTANGLE  → exact dimensions.
    TRIANGLE / POLYGON → bounding box of geometry_data vertices + product height.
                          geometry_data is expected as List[Tuple[int, int]] (x, y mm vertices).
                          Falls back to product dimensions if geometry_data is absent or malformed.
    CUSTOM     → product dimensions as fallback (warns once).
    """
    gt = product.geometry_type

    if gt == GeometryType.RECTANGLE:
        return product.width, product.depth, product.height

    if gt in (GeometryType.TRIANGLE, GeometryType.POLYGON):
        pts = product.geometry_data
        if pts and len(pts) >= 2:
            try:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bw = max(xs) - min(xs)
                bd = max(ys) - min(ys)
                if bw > 0 and bd > 0:
                    logger.warning(
                        "Product %s has geometry_type=%s — using bounding box %dx%d "
                        "(packing approximation, actual shape not enforced).",
                        product.sku, gt.name, bw, bd,
                    )
                    return bw, bd, product.height
            except (TypeError, IndexError):
                pass
        logger.warning(
            "Product %s has geometry_type=%s but geometry_data is missing or invalid "
            "— falling back to product.width/depth.",
            product.sku, gt.name,
        )
        return product.width, product.depth, product.height

    # CUSTOM
    logger.warning(
        "Product %s has geometry_type=CUSTOM — packing as rectangular bounding box.",
        product.sku,
    )
    return product.width, product.depth, product.height


# ---------------------------------------------------------------------------
# Pre-sort
# ---------------------------------------------------------------------------

def _sort_products(products: List[Product]) -> List[Product]:
    """Sort products for optimal packing order.

    Order: heavy non-fragile first (go to bottom), fragile last (land on top).
    Within each bucket, heaviest first so weight naturally layers bottom-up.
    """
    def _key(p: Product):
        return (1 if p.fragile else 0, -p.weight)
    return sorted(products, key=_key)


# ---------------------------------------------------------------------------
# Rotation helpers
# ---------------------------------------------------------------------------

def _get_rotations(product: Product) -> List[tuple]:
    """Return allowed (rw, rd, rh) orientations based on orientation_constraints.

    - UPRIGHT_ONLY  → 1 candidate: exactly as defined
    - NO_LAY_FLAT   → 2 candidates: Z-axis only (swap width/depth)
    - None          → all 6 orientations
    """
    from enums import OrientationConstraint
    w, d, h = _bounding_box(product)

    if product.orientation_constraints == OrientationConstraint.UPRIGHT_ONLY:
        return [(w, d, h)]

    if product.orientation_constraints == OrientationConstraint.NO_LAY_FLAT:
        return [(w, d, h), (d, w, h)]

    return [(w, d, h), (w, h, d), (d, w, h), (d, h, w), (h, w, d), (h, d, w)]


# ---------------------------------------------------------------------------
# Constraint checks
# ---------------------------------------------------------------------------

def _boxes_intersect(a_pos, a_size, b_pos, b_size) -> bool:
    """Axis-aligned bounding-box intersection test."""
    ax1, ay1, az1 = a_pos
    aw, ad, ah = a_size
    ax2, ay2, az2 = ax1 + aw, ay1 + ad, az1 + ah

    bx1, by1, bz1 = b_pos
    bw, bd, bh = b_size
    bx2, by2, bz2 = bx1 + bw, by1 + bd, bz1 + bh

    return not (ax2 <= bx1 or ax1 >= bx2 or ay2 <= by1 or ay1 >= by2 or az2 <= bz1 or az1 >= bz2)


def _xy_footprints_overlap(ax, ay, aw, ad, bx, by, bw, bd) -> bool:
    """Return True if two XY footprints overlap."""
    return not (ax + aw <= bx or ax >= bx + bw or ay + ad <= by or ay >= by + bd)


def _violates_stackable(x, y, z, rw, rd, container: Container) -> bool:
    """Return True if placing an item at (x,y,z) would sit above a non-stackable item."""
    for existing in container.items:
        if existing.product.stackable:
            continue
        ew = existing.placed_width or existing.product.width
        ed = existing.placed_depth or existing.product.depth
        eh = existing.placed_height or existing.product.height
        item_top_z = existing.pos_z + eh
        if z >= item_top_z and _xy_footprints_overlap(x, y, rw, rd, existing.pos_x, existing.pos_y, ew, ed):
            return True
    return False


def _has_collision(x, y, z, rw, rd, rh, container: Container) -> bool:
    for existing in container.items:
        ew = existing.placed_width or existing.product.width
        ed = existing.placed_depth or existing.product.depth
        eh = existing.placed_height or existing.product.height
        if _boxes_intersect((x, y, z), (rw, rd, rh), (existing.pos_x, existing.pos_y, existing.pos_z), (ew, ed, eh)):
            return True
    return False


# ---------------------------------------------------------------------------
# Space scoring
# ---------------------------------------------------------------------------

def _score_space(x, y, z, rw, rd, rh, product: Product, container: Container) -> float:
    """Score a candidate placement. Higher score = better fit for this product."""
    score = 0.0

    z_norm = z / container.height if container.height > 0 else 0.0

    if product.fragile:
        score += z_norm * 50.0
        item_cx = x + rw / 2.0
        item_cy = y + rd / 2.0
        dist_from_center = abs(item_cx - container.width / 2.0) + abs(item_cy - container.depth / 2.0)
        score -= dist_from_center * 0.05
    else:
        score -= z_norm * 20.0

    if product.is_flammable:
        m = FLAMMABLE_EDGE_MARGIN
        interior = (
            x >= m and y >= m and
            x + rw <= container.width - m and
            y + rd <= container.depth - m
        )
        if interior:
            score += 1000.0

    return score


# ---------------------------------------------------------------------------
# Core placement
# ---------------------------------------------------------------------------

def place_product(container: Container, product: Product) -> bool:
    """Try to place a product into a container.

    Spaces are pre-sorted by a product-specific score so the first valid
    placement is also the best-scoring one — preserving first-fit performance.
    """
    bw, bd, bh = _bounding_box(product)

    sorted_spaces = sorted(
        enumerate(container.spaces),
        key=lambda iv: -_score_space(
            iv[1][0], iv[1][1], iv[1][2],
            bw, bd, bh, product, container,
        ),
    )

    current_weight = sum(item.product.weight for item in container.items)

    for orig_idx, (x, y, z, w, d, h) in sorted_spaces:
        for rw, rd, rh in _get_rotations(product):
            if rw > w or rd > d or rh > h:
                continue
            if x < 0 or y < 0 or z < 0:
                continue
            if x + rw > container.width or y + rd > container.depth or z + rh > container.height:
                continue
            if current_weight + product.weight > container.max_weight:
                continue
            if _has_collision(x, y, z, rw, rd, rh, container):
                continue
            if _violates_stackable(x, y, z, rw, rd, container):
                logger.debug("Skipping %s at (%s,%s,%s): above non-stackable item", product.sku, x, y, z)
                continue

            container.items.append(PlacedItem(
                product=product,
                pos_x=x, pos_y=y, pos_z=z,
                placed_width=rw, placed_depth=rd, placed_height=rh,
            ))
            logger.debug("Placed %s at (%s,%s,%s) size (%s,%s,%s)", product.sku, x, y, z, rw, rd, rh)

            # Guillotine split
            container.spaces.pop(orig_idx)

            nx, ny, nz = x + rw, y, z
            nw = min(w - rw, max(0, container.width - nx))
            if nw > 0 and nx < container.width:
                container.spaces.append((nx, ny, nz, nw, d, h))

            fx, fy, fz = x, y + rd, z
            fw = min(rw, max(0, container.width - fx))
            fd = min(d - rd, max(0, container.depth - fy))
            if fw > 0 and fd > 0 and fx < container.width and fy < container.depth:
                container.spaces.append((fx, fy, fz, fw, fd, h))

            tx, ty, tz = x, y, z + rh
            tw = min(rw, max(0, container.width - tx))
            td = min(rd, max(0, container.depth - ty))
            th = min(h - rh, max(0, container.height - tz))
            if tw > 0 and td > 0 and th > 0 and tx < container.width and ty < container.depth and tz < container.height:
                container.spaces.append((tx, ty, tz, tw, td, th))

            return True

    return False


# ---------------------------------------------------------------------------
# Triangle pairing
# ---------------------------------------------------------------------------

def _can_pair_triangles(a: Product, b: Product) -> bool:
    """Two TRIANGLE products can share a rectangle slot if their bounding boxes match."""
    return (
        a.geometry_type == GeometryType.TRIANGLE
        and b.geometry_type == GeometryType.TRIANGLE
        and _bounding_box(a) == _bounding_box(b)
    )


def _place_paired_triangles(container: Container, a: Product, b: Product) -> bool:
    """Place two compatible triangles into one shared bounding-box slot.

    Both items are recorded at the same (x, y, z) with the same placed dimensions.
    The second item is flagged pair_second=True so the visualiser renders the
    complement (point-reflected) shape, and together they fill a full rectangle.
    Space is consumed exactly once, halving the wasted area vs. two solo placements.
    """
    pair_uid = uuid.uuid4().hex[:8]

    current_weight = sum(item.product.weight for item in container.items)
    if current_weight + a.weight + b.weight > container.max_weight:
        return False

    sorted_spaces = sorted(
        enumerate(container.spaces),
        key=lambda iv: -_score_space(
            iv[1][0], iv[1][1], iv[1][2], *_bounding_box(a), a, container,
        ),
    )

    for orig_idx, (x, y, z, w, d, h) in sorted_spaces:
        for rw, rd, rh in _get_rotations(a):
            if rw > w or rd > d or rh > h:
                continue
            if x < 0 or y < 0 or z < 0:
                continue
            if x + rw > container.width or y + rd > container.depth or z + rh > container.height:
                continue
            if _has_collision(x, y, z, rw, rd, rh, container):
                continue
            if _violates_stackable(x, y, z, rw, rd, container):
                continue

            pair_uid_str = uuid.uuid4().hex[:8]
            container.items.append(PlacedItem(
                product=a,
                pos_x=x, pos_y=y, pos_z=z,
                placed_width=rw, placed_depth=rd, placed_height=rh,
                pair_id=pair_uid_str, pair_second=False,
            ))
            container.items.append(PlacedItem(
                product=b,
                pos_x=x, pos_y=y, pos_z=z,
                placed_width=rw, placed_depth=rd, placed_height=rh,
                pair_id=pair_uid_str, pair_second=True,
            ))
            logger.debug(
                "Paired %s+%s at (%s,%s,%s) size (%s,%s,%s) [pair=%s]",
                a.sku, b.sku, x, y, z, rw, rd, rh, pair_uid_str,
            )

            # Guillotine split — identical to single-item placement
            container.spaces.pop(orig_idx)

            nx, ny, nz = x + rw, y, z
            nw = min(w - rw, max(0, container.width - nx))
            if nw > 0 and nx < container.width:
                container.spaces.append((nx, ny, nz, nw, d, h))

            fx, fy, fz = x, y + rd, z
            fw = min(rw, max(0, container.width - fx))
            fd = min(d - rd, max(0, container.depth - fy))
            if fw > 0 and fd > 0 and fx < container.width and fy < container.depth:
                container.spaces.append((fx, fy, fz, fw, fd, h))

            tx, ty, tz = x, y, z + rh
            tw = min(rw, max(0, container.width - tx))
            td = min(rd, max(0, container.depth - ty))
            th = min(h - rh, max(0, container.height - tz))
            if tw > 0 and td > 0 and th > 0 and tx < container.width and ty < container.depth and tz < container.height:
                container.spaces.append((tx, ty, tz, tw, td, th))

            return True

    return False

def pack_products(products: List[Product], first_pallet: Container) -> List[Container]:
    """Pack a list of products into containers.

    Before attempting solo placement, compatible TRIANGLE pairs are identified
    and packed together into one shared bounding-box slot, halving wasted space.
    """
    pallets = [first_pallet]
    products_to_place = _sort_products(products)
    pallet_index = 1

    while products_to_place:
        pallet = pallets[-1]
        remaining: List[Product] = []
        any_placed = False
        skip_indices: set[int] = set()

        for i, product in enumerate(products_to_place):
            if i in skip_indices:
                continue

            placed = False

            # Try to pair with a compatible triangle partner
            if product.geometry_type == GeometryType.TRIANGLE:
                for j in range(i + 1, len(products_to_place)):
                    if j in skip_indices:
                        continue
                    partner = products_to_place[j]
                    if _can_pair_triangles(product, partner):
                        if _place_paired_triangles(pallet, product, partner):
                            skip_indices.add(j)
                            any_placed = True
                            placed = True
                            break

            if not placed and place_product(pallet, product):
                any_placed = True
                placed = True

            if not placed:
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

    for p in pallets:
        center_items_in_container(p)

    return pallets


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def center_items_in_container(container: Container) -> None:
    """Translate all placed items so their X/Y bounding box is centered on the pallet."""
    if not container.items:
        return

    min_x = min(item.pos_x for item in container.items)
    min_y = min(item.pos_y for item in container.items)
    max_x = max(item.pos_x + item.rotated_width for item in container.items)
    max_y = max(item.pos_y + item.rotated_depth for item in container.items)

    dx = container.width / 2.0 - (min_x + max_x) / 2.0
    dy = container.depth / 2.0 - (min_y + max_y) / 2.0

    dx = max(dx, -min_x) if dx < 0 else min(dx, container.width - max_x)
    dy = max(dy, -min_y) if dy < 0 else min(dy, container.depth - max_y)

    if dx == 0 and dy == 0:
        return

    for item in container.items:
        item.pos_x = int(round(item.pos_x + dx))
        item.pos_y = int(round(item.pos_y + dy))

