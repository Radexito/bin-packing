"""Unit tests for the JSON exporter."""
import json
import tempfile
from pathlib import Path

import pytest

from models.product import Product, GeometryType
from models.container import Container
from models.placed_item import PlacedItem
from enums import HazardClass
from exporter import export_to_json


def _make_container_with_items() -> Container:
    c = Container(name="Pallet-1", width=1200, depth=800, height=1500, max_weight=1_000_000)
    p = Product(sku="SKU1", name="box", width=100, depth=200, height=300, weight=500,
                fragile=True, hazard_classes=[HazardClass.CLASS_3])
    c.items.append(PlacedItem(
        product=p, pos_x=10, pos_y=20, pos_z=30,
        placed_width=100, placed_depth=200, placed_height=300,
    ))
    return c


def _make_tri_container() -> Container:
    c = Container(name="Pallet-T", width=1200, depth=800, height=1500, max_weight=1_000_000)
    tri = Product(sku="TRI", width=300, depth=200, height=150, weight=1000,
                  geometry_type=GeometryType.TRIANGLE,
                  geometry_data=[(0, 0), (300, 0), (0, 200)])
    c.items.append(PlacedItem(
        product=tri, pos_x=0, pos_y=0, pos_z=0,
        placed_width=300, placed_depth=200, placed_height=150,
        pair_id="abc123", pair_second=False,
    ))
    c.items.append(PlacedItem(
        product=tri, pos_x=0, pos_y=0, pos_z=0,
        placed_width=300, placed_depth=200, placed_height=150,
        pair_id="abc123", pair_second=True,
    ))
    return c


class TestExporterSchema:
    def test_output_has_pallets_key(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        assert "pallets" in data

    def test_pallet_has_required_keys(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        pallet = data["pallets"][0]
        assert "name" in pallet
        assert "dimensions" in pallet
        assert "items" in pallet

    def test_pallet_dimensions_correct(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        dims = data["pallets"][0]["dimensions"]
        assert dims["width"] == 1200
        assert dims["depth"] == 800
        assert dims["height"] == 1500

    def test_item_has_position_and_placed_dimensions(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        item = data["pallets"][0]["items"][0]
        assert "position" in item
        assert "placed_dimensions" in item
        assert "product" in item

    def test_item_position_values(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        pos = data["pallets"][0]["items"][0]["position"]
        assert pos["pos_x"] == 10
        assert pos["pos_y"] == 20
        assert pos["pos_z"] == 30

    def test_item_placed_dimensions_values(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        dims = data["pallets"][0]["items"][0]["placed_dimensions"]
        assert dims["width"] == 100
        assert dims["depth"] == 200
        assert dims["height"] == 300

    def test_product_fields_serialized(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        prod = data["pallets"][0]["items"][0]["product"]
        assert prod["sku"] == "SKU1"
        assert prod["fragile"] is True

    def test_pair_fields_present_for_triangle_items(self):
        c = _make_tri_container()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        items = data["pallets"][0]["items"]
        pair_ids = [it.get("pair_id") for it in items]
        assert all(pid == "abc123" for pid in pair_ids)
        pair_seconds = [it.get("pair_second") for it in items]
        assert False in pair_seconds
        assert True in pair_seconds

    def test_multiple_pallets_exported(self):
        c1 = _make_container_with_items()
        c2 = Container(name="Pallet-2", width=1200, depth=800, height=1500, max_weight=1_000_000)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c1, c2], path)
        data = json.loads(Path(path).read_text())
        assert len(data["pallets"]) == 2

    def test_empty_pallet_items_list(self):
        c = Container(name="Empty", width=1200, depth=800, height=1500, max_weight=1_000_000)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        data = json.loads(Path(path).read_text())
        assert data["pallets"][0]["items"] == []

    def test_output_is_valid_json(self):
        c = _make_container_with_items()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        export_to_json([c], path)
        content = Path(path).read_text()
        parsed = json.loads(content)  # should not raise
        assert isinstance(parsed, dict)
