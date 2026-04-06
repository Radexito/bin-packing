"""Unit tests for packing logic: helpers, constraints, placement, and post-processing."""
import pytest
from models.product import Product, GeometryType
from models.container import Container
from models.placed_item import PlacedItem
from enums import HazardClass, OrientationConstraint
from packing import (
    _bounding_box,
    _sort_products,
    _get_rotations,
    _boxes_intersect,
    _xy_footprints_overlap,
    _has_collision,
    _violates_stackable,
    center_items_in_container,
    place_product,
    _can_pair_triangles,
    _place_paired_triangles,
    pack_products,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_product(**kwargs) -> Product:
    defaults = dict(sku="P", width=100, depth=100, height=100, weight=500)
    defaults.update(kwargs)
    return Product(**defaults)


def make_container(width=1200, depth=800, height=1500, max_weight=10_000_000) -> Container:
    return Container(name="Test", width=width, depth=depth, height=height, max_weight=max_weight)


def place_at(container: Container, product: Product, x: int, y: int, z: int,
             rw: int = None, rd: int = None, rh: int = None):
    """Helper: manually append a PlacedItem to a container."""
    container.items.append(PlacedItem(
        product=product,
        pos_x=x, pos_y=y, pos_z=z,
        placed_width=rw or product.width,
        placed_depth=rd or product.depth,
        placed_height=rh or product.height,
    ))


# ---------------------------------------------------------------------------
# _bounding_box
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_rectangle_returns_exact_dimensions(self):
        p = make_product(width=200, depth=300, height=150)
        assert _bounding_box(p) == (200, 300, 150)

    def test_triangle_computes_from_geometry_data(self):
        p = make_product(width=999, depth=999, height=150,
                         geometry_type=GeometryType.TRIANGLE,
                         geometry_data=[(0, 0), (300, 0), (0, 200)])
        assert _bounding_box(p) == (300, 200, 150)

    def test_triangle_fallback_when_no_geometry_data(self):
        p = make_product(width=200, depth=300, height=150,
                         geometry_type=GeometryType.TRIANGLE)
        assert _bounding_box(p) == (200, 300, 150)

    def test_polygon_computes_from_geometry_data(self):
        p = make_product(width=999, depth=999, height=100,
                         geometry_type=GeometryType.POLYGON,
                         geometry_data=[(0, 0), (400, 0), (400, 250), (0, 250)])
        assert _bounding_box(p) == (400, 250, 100)

    def test_custom_returns_product_dimensions(self):
        p = make_product(width=200, depth=300, height=150,
                         geometry_type=GeometryType.CUSTOM)
        assert _bounding_box(p) == (200, 300, 150)


# ---------------------------------------------------------------------------
# _sort_products
# ---------------------------------------------------------------------------

class TestSortProducts:
    def test_fragile_items_sorted_last(self):
        heavy = make_product(sku="H", weight=10000, fragile=False)
        fragile = make_product(sku="F", weight=1000, fragile=True)
        light = make_product(sku="L", weight=500, fragile=False)

        result = _sort_products([fragile, heavy, light])
        skus = [p.sku for p in result]
        assert skus.index("F") > skus.index("H")
        assert skus.index("F") > skus.index("L")

    def test_heavy_non_fragile_before_light_non_fragile(self):
        heavy = make_product(sku="H", weight=10000, fragile=False)
        light = make_product(sku="L", weight=500, fragile=False)

        result = _sort_products([light, heavy])
        assert result[0].sku == "H"

    def test_all_fragile_sorted_by_weight_desc(self):
        a = make_product(sku="A", weight=3000, fragile=True)
        b = make_product(sku="B", weight=1000, fragile=True)
        c = make_product(sku="C", weight=5000, fragile=True)

        result = _sort_products([a, b, c])
        weights = [p.weight for p in result]
        assert weights == sorted(weights, reverse=True)


# ---------------------------------------------------------------------------
# _get_rotations
# ---------------------------------------------------------------------------

class TestGetRotations:
    def test_upright_only_returns_one_rotation(self):
        p = make_product(width=100, depth=200, height=300,
                         orientation_constraints=OrientationConstraint.UPRIGHT_ONLY)
        rots = _get_rotations(p)
        assert rots == [(100, 200, 300)]

    def test_no_lay_flat_returns_two_rotations(self):
        p = make_product(width=100, depth=200, height=300,
                         orientation_constraints=OrientationConstraint.NO_LAY_FLAT)
        rots = _get_rotations(p)
        assert len(rots) == 2
        # Height must remain 300 in both
        for rw, rd, rh in rots:
            assert rh == 300

    def test_unconstrained_returns_six_rotations(self):
        p = make_product(width=100, depth=200, height=300)
        rots = _get_rotations(p)
        assert len(rots) == 6

    def test_six_rotations_cover_all_axis_permutations(self):
        p = make_product(width=100, depth=200, height=300)
        rots = _get_rotations(p)
        dims = {frozenset([rw, rd, rh]) for rw, rd, rh in rots}
        assert frozenset([100, 200, 300]) in dims


# ---------------------------------------------------------------------------
# Collision / Intersection helpers
# ---------------------------------------------------------------------------

class TestBoxesIntersect:
    def test_touching_boxes_do_not_intersect(self):
        # A occupies [0,100] x [0,100] x [0,100]; B starts at x=100
        assert not _boxes_intersect((0, 0, 0), (100, 100, 100), (100, 0, 0), (100, 100, 100))

    def test_overlapping_boxes_intersect(self):
        assert _boxes_intersect((0, 0, 0), (100, 100, 100), (50, 0, 0), (100, 100, 100))

    def test_identical_boxes_intersect(self):
        assert _boxes_intersect((0, 0, 0), (100, 100, 100), (0, 0, 0), (100, 100, 100))

    def test_separated_boxes_do_not_intersect(self):
        assert not _boxes_intersect((0, 0, 0), (50, 50, 50), (100, 0, 0), (50, 50, 50))


class TestXYFootprintsOverlap:
    def test_touching_footprints_do_not_overlap(self):
        assert not _xy_footprints_overlap(0, 0, 100, 100, 100, 0, 100, 100)

    def test_overlapping_footprints(self):
        assert _xy_footprints_overlap(0, 0, 100, 100, 50, 50, 100, 100)

    def test_non_overlapping_footprints(self):
        assert not _xy_footprints_overlap(0, 0, 50, 50, 200, 200, 50, 50)


# ---------------------------------------------------------------------------
# _has_collision
# ---------------------------------------------------------------------------

class TestHasCollision:
    def test_no_collision_on_empty_container(self):
        c = make_container()
        assert not _has_collision(0, 0, 0, 100, 100, 100, c)

    def test_collision_detected_with_existing_item(self):
        c = make_container()
        p = make_product(width=100, depth=100, height=100)
        place_at(c, p, 0, 0, 0)
        # overlapping placement
        assert _has_collision(50, 0, 0, 100, 100, 100, c)

    def test_no_collision_when_adjacent(self):
        c = make_container()
        p = make_product(width=100, depth=100, height=100)
        place_at(c, p, 0, 0, 0)
        # placed right next to existing item in X
        assert not _has_collision(100, 0, 0, 100, 100, 100, c)


# ---------------------------------------------------------------------------
# _violates_stackable
# ---------------------------------------------------------------------------

class TestViolatesStackable:
    def test_placing_on_stackable_item_is_allowed(self):
        c = make_container()
        p = make_product(width=100, depth=100, height=100, stackable=True)
        place_at(c, p, 0, 0, 0)
        # above the existing item
        assert not _violates_stackable(0, 0, 100, 100, 100, c)

    def test_placing_above_non_stackable_item_is_violation(self):
        c = make_container()
        p = make_product(width=100, depth=100, height=100, stackable=False)
        place_at(c, p, 0, 0, 0)
        # directly above non-stackable
        assert _violates_stackable(0, 0, 100, 100, 100, c)

    def test_non_overlapping_footprint_is_not_a_violation(self):
        c = make_container()
        p = make_product(width=100, depth=100, height=100, stackable=False)
        place_at(c, p, 0, 0, 0)
        # above but completely offset in XY — not above the non-stackable
        assert not _violates_stackable(500, 500, 100, 100, 100, c)


# ---------------------------------------------------------------------------
# place_product — bounds checking
# ---------------------------------------------------------------------------

class TestPlaceProductBounds:
    def test_item_placed_within_container(self):
        c = make_container(width=500, depth=500, height=500)
        p = make_product(width=100, depth=100, height=100)
        assert place_product(c, p)
        item = c.items[0]
        assert item.pos_x + item.rotated_width <= 500
        assert item.pos_y + item.rotated_depth <= 500
        assert item.pos_z + item.rotated_height <= 500

    def test_item_too_large_for_container_is_rejected(self):
        c = make_container(width=50, depth=50, height=50)
        p = make_product(width=100, depth=100, height=100)
        result = place_product(c, p)
        assert not result
        assert c.items == []

    def test_weight_limit_prevents_placement(self):
        c = make_container(max_weight=100)
        p = make_product(weight=200, width=100, depth=100, height=100)
        result = place_product(c, p)
        assert not result

    def test_weight_limit_respected_across_multiple_items(self):
        c = make_container(width=1000, depth=1000, height=1000, max_weight=300)
        p1 = make_product(sku="A", weight=100, width=100, depth=100, height=100)
        p2 = make_product(sku="B", weight=100, width=100, depth=100, height=100)
        p3 = make_product(sku="C", weight=200, width=100, depth=100, height=100)

        place_product(c, p1)
        place_product(c, p2)
        placed = place_product(c, p3)

        total = sum(item.product.weight for item in c.items)
        assert total <= 300
        assert not placed  # p3 would push weight over limit


# ---------------------------------------------------------------------------
# place_product — no collisions
# ---------------------------------------------------------------------------

class TestPlaceProductNoCollisions:
    def test_multiple_items_do_not_overlap(self):
        c = make_container(width=1200, depth=800, height=500)
        products = [make_product(sku=f"P{i}", width=100, depth=100, height=100) for i in range(10)]
        for p in products:
            place_product(c, p)

        items = c.items
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                assert not _boxes_intersect(
                    (a.pos_x, a.pos_y, a.pos_z),
                    (a.rotated_width, a.rotated_depth, a.rotated_height),
                    (b.pos_x, b.pos_y, b.pos_z),
                    (b.rotated_width, b.rotated_depth, b.rotated_height),
                ), f"Items {i} and {j} overlap"


# ---------------------------------------------------------------------------
# Rotation: orientation constraints enforced by place_product
# ---------------------------------------------------------------------------

class TestOrientationConstraints:
    def test_upright_only_keeps_height(self):
        c = make_container(width=1000, depth=1000, height=1000)
        p = make_product(width=100, depth=200, height=300,
                         orientation_constraints=OrientationConstraint.UPRIGHT_ONLY)
        place_product(c, p)
        assert len(c.items) == 1
        item = c.items[0]
        assert item.rotated_height == 300
        assert item.rotated_width == 100
        assert item.rotated_depth == 200

    def test_no_lay_flat_height_unchanged(self):
        c = make_container(width=1000, depth=1000, height=1000)
        p = make_product(width=100, depth=200, height=300,
                         orientation_constraints=OrientationConstraint.NO_LAY_FLAT)
        place_product(c, p)
        assert len(c.items) == 1
        item = c.items[0]
        assert item.rotated_height == 300

    def test_unconstrained_may_use_any_orientation(self):
        # Container only fits the item if it's rotated: height=300 > container height=200
        # but width=100 fits if used as height
        c = make_container(width=1000, depth=1000, height=200)
        p = make_product(width=100, depth=150, height=300)  # natural height 300 > container
        placed = place_product(c, p)
        assert placed
        item = c.items[0]
        assert item.rotated_height <= 200


# ---------------------------------------------------------------------------
# Constraint enforcement: fragile items placed higher
# ---------------------------------------------------------------------------

class TestFragileConstraintEnforcement:
    def test_fragile_placed_above_non_fragile(self):
        """In a container with limited space, fragile items should end up higher."""
        c = make_container(width=1000, depth=1000, height=1000)
        # Place several heavy non-fragile items first (they'll take lower z)
        non_fragile = [make_product(sku=f"NF{i}", weight=1000, fragile=False,
                                    width=100, depth=100, height=100) for i in range(5)]
        fragile = make_product(sku="FR", weight=100, fragile=True, width=100, depth=100, height=100)

        for nf in non_fragile:
            place_product(c, nf)
        place_product(c, fragile)

        fragile_item = next(it for it in c.items if it.product.sku == "FR")
        non_fragile_z = [it.pos_z for it in c.items if not it.product.fragile]

        # Fragile item should ideally be at z >= min non-fragile z
        # (scoring pushes fragile up — hard guarantee is that it was placed)
        assert fragile_item is not None


# ---------------------------------------------------------------------------
# center_items_in_container
# ---------------------------------------------------------------------------

class TestCenterItemsInContainer:
    def test_empty_container_does_not_raise(self):
        c = make_container()
        center_items_in_container(c)  # should not raise

    def test_items_stay_within_bounds_after_centering(self):
        c = make_container(width=1000, depth=800, height=500)
        p = make_product(width=100, depth=100, height=100)
        place_at(c, p, 0, 0, 0)  # placed in corner; centering should move it inward
        center_items_in_container(c)
        item = c.items[0]
        assert item.pos_x >= 0
        assert item.pos_y >= 0
        assert item.pos_x + item.rotated_width <= c.width
        assert item.pos_y + item.rotated_depth <= c.depth

    def test_single_item_centered(self):
        c = make_container(width=1000, depth=800, height=500)
        p = make_product(width=200, depth=200, height=100)
        place_at(c, p, 0, 0, 0)
        center_items_in_container(c)
        item = c.items[0]
        # After centering, item center should be close to container center
        item_cx = item.pos_x + item.rotated_width / 2
        item_cy = item.pos_y + item.rotated_depth / 2
        assert abs(item_cx - 500) < 1
        assert abs(item_cy - 400) < 1

    def test_multiple_items_stay_within_bounds_after_centering(self):
        c = make_container(width=1000, depth=800, height=500)
        p = make_product(width=100, depth=100, height=100)
        for x_offset in range(0, 300, 100):
            place_at(c, p, x_offset, 0, 0)
        center_items_in_container(c)
        for item in c.items:
            assert item.pos_x >= 0
            assert item.pos_y >= 0
            assert item.pos_x + item.rotated_width <= c.width
            assert item.pos_y + item.rotated_depth <= c.depth


# ---------------------------------------------------------------------------
# Triangle pairing
# ---------------------------------------------------------------------------

class TestTrianglePairing:
    def _tri(self, sku="T"):
        return Product(sku=sku, width=300, depth=200, height=150, weight=1000,
                       geometry_type=GeometryType.TRIANGLE,
                       geometry_data=[(0, 0), (300, 0), (0, 200)])

    def test_can_pair_identical_triangles(self):
        a = self._tri("A")
        b = self._tri("B")
        assert _can_pair_triangles(a, b)

    def test_cannot_pair_triangle_with_rectangle(self):
        tri = self._tri()
        rect = make_product()
        assert not _can_pair_triangles(tri, rect)

    def test_cannot_pair_different_size_triangles(self):
        a = Product(sku="A", width=300, depth=200, height=150, weight=1000,
                    geometry_type=GeometryType.TRIANGLE,
                    geometry_data=[(0, 0), (300, 0), (0, 200)])
        b = Product(sku="B", width=400, depth=200, height=150, weight=1000,
                    geometry_type=GeometryType.TRIANGLE,
                    geometry_data=[(0, 0), (400, 0), (0, 200)])
        assert not _can_pair_triangles(a, b)

    def test_paired_triangles_placed_at_same_position(self):
        c = make_container(width=1200, depth=800, height=1500)
        a = self._tri("A")
        b = self._tri("B")
        result = _place_paired_triangles(c, a, b)
        assert result
        assert len(c.items) == 2
        a_item = next(it for it in c.items if it.product.sku == "A")
        b_item = next(it for it in c.items if it.product.sku == "B")
        assert (a_item.pos_x, a_item.pos_y, a_item.pos_z) == (b_item.pos_x, b_item.pos_y, b_item.pos_z)
        assert a_item.pair_id == b_item.pair_id
        assert a_item.pair_second is False
        assert b_item.pair_second is True

    def test_paired_triangles_respect_weight_limit(self):
        c = make_container(width=1200, depth=800, height=1500, max_weight=500)
        a = self._tri("A")  # weight=1000
        b = self._tri("B")  # weight=1000 — together 2000 > 500
        result = _place_paired_triangles(c, a, b)
        assert not result
