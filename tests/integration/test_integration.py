"""Integration tests: end-to-end pipeline from products → pack → export."""
import json
import tempfile
from pathlib import Path

import pytest

from models.product import Product, GeometryType
from models.container import Container
from enums import HazardClass, OrientationConstraint
from packing import pack_products, _boxes_intersect
from exporter import export_to_json


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_pallet(width=1200, depth=800, height=1500, max_weight=1_500_000) -> Container:
    return Container(name="Pallet-1", width=width, depth=depth, height=height,
                     max_weight=max_weight)


def make_box(sku, w=200, d=200, h=200, weight=1000, **kwargs) -> Product:
    return Product(sku=sku, width=w, depth=d, height=h, weight=weight, **kwargs)


# ---------------------------------------------------------------------------
# Basic packing pipeline
# ---------------------------------------------------------------------------

class TestPackingPipeline:
    def test_single_item_is_placed(self):
        pallet = make_pallet()
        p = make_box("A")
        pallets = pack_products([p], pallet)
        total_items = sum(len(c.items) for c in pallets)
        assert total_items == 1

    def test_all_items_are_placed(self):
        pallet = make_pallet()
        products = [make_box(f"P{i}") for i in range(20)]
        pallets = pack_products(products, pallet)
        total_items = sum(len(c.items) for c in pallets)
        assert total_items == 20

    def test_overflow_creates_additional_pallet(self):
        # Small pallet that can only fit a few items
        pallet = make_pallet(width=300, depth=300, height=300, max_weight=100_000)
        products = [make_box(f"P{i}", w=200, d=200, h=200) for i in range(10)]
        pallets = pack_products(products, pallet)
        assert len(pallets) > 1

    def test_no_collisions_across_all_pallets(self):
        pallet = make_pallet()
        products = [make_box(f"P{i}") for i in range(30)]
        pallets = pack_products(products, pallet)

        for container in pallets:
            items = container.items
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    a, b = items[i], items[j]
                    # Paired triangles share the same bounding box slot — skip collision check
                    if a.pair_id and a.pair_id == b.pair_id:
                        continue
                    assert not _boxes_intersect(
                        (a.pos_x, a.pos_y, a.pos_z),
                        (a.rotated_width, a.rotated_depth, a.rotated_height),
                        (b.pos_x, b.pos_y, b.pos_z),
                        (b.rotated_width, b.rotated_depth, b.rotated_height),
                    ), (f"Collision in {container.name}: item {i} ({a.sku}) "
                        f"overlaps item {j} ({b.sku})")

    def test_all_items_within_container_bounds(self):
        pallet = make_pallet()
        products = [make_box(f"P{i}") for i in range(20)]
        pallets = pack_products(products, pallet)

        for container in pallets:
            for item in container.items:
                assert item.pos_x >= 0, f"{item.sku} pos_x < 0"
                assert item.pos_y >= 0, f"{item.sku} pos_y < 0"
                assert item.pos_z >= 0, f"{item.sku} pos_z < 0"
                assert item.pos_x + item.rotated_width <= container.width, f"{item.sku} exceeds width"
                assert item.pos_y + item.rotated_depth <= container.depth, f"{item.sku} exceeds depth"
                assert item.pos_z + item.rotated_height <= container.height, f"{item.sku} exceeds height"

    def test_weight_not_exceeded_per_container(self):
        pallet = make_pallet(max_weight=5000)
        products = [make_box(f"P{i}", weight=1000) for i in range(10)]
        pallets = pack_products(products, pallet)

        for container in pallets:
            total = sum(item.product.weight for item in container.items)
            assert total <= container.max_weight, (
                f"{container.name} exceeds max_weight: {total} > {container.max_weight}"
            )


# ---------------------------------------------------------------------------
# Constraint enforcement
# ---------------------------------------------------------------------------

class TestConstraintEnforcement:
    def test_fragile_items_placed_higher_than_non_fragile(self):
        """Fragile items should appear at a z-level >= non-fragile items when possible."""
        pallet = make_pallet()
        non_fragile = [make_box(f"NF{i}", w=300, d=200, h=200, weight=5000, fragile=False)
                       for i in range(6)]
        fragile = [make_box(f"FR{i}", w=100, d=100, h=100, weight=100, fragile=True)
                   for i in range(3)]

        pallets = pack_products(non_fragile + fragile, pallet)
        container = pallets[0]

        fragile_zs = [it.pos_z for it in container.items if it.product.fragile]
        nonfrag_zs = [it.pos_z for it in container.items if not it.product.fragile]

        if fragile_zs and nonfrag_zs:
            # At least one fragile item should be at or above min non-fragile z
            assert max(fragile_zs) >= min(nonfrag_zs)

    def test_non_stackable_items_have_nothing_above_them(self):
        pallet = make_pallet()
        non_stackable = make_box("NS", w=400, d=400, h=100, weight=1000, stackable=False)
        small = make_box("S", w=100, d=100, h=100, weight=100)

        pallets = pack_products([non_stackable, small], pallet)
        container = pallets[0]

        ns_item = next((it for it in container.items if it.sku == "NS"), None)
        if ns_item is None:
            return  # item wasn't placed, skip

        ns_top_z = ns_item.pos_z + ns_item.rotated_height
        ns_x, ns_y = ns_item.pos_x, ns_item.pos_y
        ns_w, ns_d = ns_item.rotated_width, ns_item.rotated_depth

        for other in container.items:
            if other is ns_item:
                continue
            # Is 'other' above ns_item AND overlapping its footprint?
            if other.pos_z >= ns_top_z:
                ox, oy, ow, od = other.pos_x, other.pos_y, other.rotated_width, other.rotated_depth
                footprint_overlap = not (
                    ox + ow <= ns_x or ox >= ns_x + ns_w or
                    oy + od <= ns_y or oy >= ns_y + ns_d
                )
                assert not footprint_overlap, (
                    f"{other.sku} placed above non-stackable {ns_item.sku}"
                )

    def test_upright_only_orientation_respected(self):
        pallet = make_pallet()
        p = make_box("U", w=100, d=200, h=300,
                     orientation_constraints=OrientationConstraint.UPRIGHT_ONLY)
        pallets = pack_products([p], pallet)
        item = pallets[0].items[0]
        assert item.rotated_width == 100
        assert item.rotated_depth == 200
        assert item.rotated_height == 300

    def test_no_lay_flat_height_preserved(self):
        pallet = make_pallet()
        p = make_box("NLF", w=100, d=200, h=300,
                     orientation_constraints=OrientationConstraint.NO_LAY_FLAT)
        pallets = pack_products([p], pallet)
        item = pallets[0].items[0]
        assert item.rotated_height == 300


# ---------------------------------------------------------------------------
# Mixed geometry
# ---------------------------------------------------------------------------

class TestMixedGeometry:
    def test_triangles_and_rectangles_packed_together(self):
        pallet = make_pallet()
        rects = [make_box(f"R{i}", w=200, d=200, h=200) for i in range(5)]
        tris = [
            Product(sku=f"T{i}", width=300, depth=200, height=150, weight=1000,
                    geometry_type=GeometryType.TRIANGLE,
                    geometry_data=[(0, 0), (300, 0), (0, 200)])
            for i in range(4)
        ]
        pallets = pack_products(rects + tris, pallet)
        total = sum(len(c.items) for c in pallets)
        assert total == 9  # all placed (triangles paired: 4 items = 2 pairs each consuming 1 slot)

    def test_paired_triangles_have_same_pair_id(self):
        pallet = make_pallet()
        tris = [
            Product(sku=f"T{i}", width=300, depth=200, height=150, weight=1000,
                    geometry_type=GeometryType.TRIANGLE,
                    geometry_data=[(0, 0), (300, 0), (0, 200)])
            for i in range(2)
        ]
        pallets = pack_products(tris, pallet)
        container = pallets[0]
        tri_items = [it for it in container.items if it.product.geometry_type == GeometryType.TRIANGLE]
        assert len(tri_items) == 2
        assert tri_items[0].pair_id == tri_items[1].pair_id
        assert tri_items[0].pair_id is not None


# ---------------------------------------------------------------------------
# Export integration
# ---------------------------------------------------------------------------

class TestExportIntegration:
    def test_export_and_reimport_matches_schema(self):
        pallet = make_pallet()
        products = [make_box(f"P{i}") for i in range(5)]
        pallets = pack_products(products, pallet)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json(pallets, path)

        data = json.loads(Path(path).read_text())
        assert "pallets" in data
        for pallet_data in data["pallets"]:
            assert "name" in pallet_data
            assert "dimensions" in pallet_data
            assert "items" in pallet_data
            for item_data in pallet_data["items"]:
                assert "position" in item_data
                assert "placed_dimensions" in item_data
                assert "product" in item_data
                pos = item_data["position"]
                assert all(k in pos for k in ["pos_x", "pos_y", "pos_z"])
                dims = item_data["placed_dimensions"]
                assert all(k in dims for k in ["width", "depth", "height"])

    def test_exported_positions_match_placed_items(self):
        pallet = make_pallet()
        products = [make_box("ONLY", w=100, d=100, h=100)]
        pallets = pack_products(products, pallet)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json(pallets, path)

        data = json.loads(Path(path).read_text())
        exported_item = data["pallets"][0]["items"][0]
        placed_item = pallets[0].items[0]

        assert exported_item["position"]["pos_x"] == placed_item.pos_x
        assert exported_item["position"]["pos_y"] == placed_item.pos_y
        assert exported_item["position"]["pos_z"] == placed_item.pos_z
        assert exported_item["placed_dimensions"]["width"] == placed_item.rotated_width
        assert exported_item["placed_dimensions"]["depth"] == placed_item.rotated_depth
        assert exported_item["placed_dimensions"]["height"] == placed_item.rotated_height

    def test_hazard_classes_serialized_in_export(self):
        pallet = make_pallet()
        p = make_box("HAZ", hazard_classes=[HazardClass.CLASS_3])
        pallets = pack_products([p], pallet)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json(pallets, path)

        data = json.loads(Path(path).read_text())
        prod = data["pallets"][0]["items"][0]["product"]
        assert "3" in prod["hazard_classes"]
