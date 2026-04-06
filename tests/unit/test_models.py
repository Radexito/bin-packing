"""Unit tests for Product, Container, and PlacedItem models."""
import pytest
from models.product import Product, GeometryType
from models.container import Container
from models.placed_item import PlacedItem
from enums import HazardClass, OrientationConstraint


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class TestProduct:
    def test_basic_creation(self):
        p = Product(sku="X1", width=100, depth=200, height=300, weight=500)
        assert p.sku == "X1"
        assert p.width == 100
        assert p.depth == 200
        assert p.height == 300
        assert p.weight == 500

    def test_defaults(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100)
        assert p.fragile is False
        assert p.stackable is True
        assert p.hazard_classes == []
        assert p.geometry_type == GeometryType.RECTANGLE
        assert p.geometry_data is None

    def test_is_flammable_false_by_default(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100)
        assert p.is_flammable is False

    def test_is_flammable_true_for_class_3(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    hazard_classes=[HazardClass.CLASS_3])
        assert p.is_flammable is True

    def test_is_flammable_true_for_class_2_1(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    hazard_classes=[HazardClass.CLASS_2_1])
        assert p.is_flammable is True

    def test_is_flammable_false_for_class_2_2(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    hazard_classes=[HazardClass.CLASS_2_2])
        assert p.is_flammable is False

    def test_requires_segregation(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    hazard_classes=[HazardClass.CLASS_1_1])
        assert p.requires_segregation is True

    def test_requires_segregation_class_9_false(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    hazard_classes=[HazardClass.CLASS_9])
        assert p.requires_segregation is False

    def test_geometry_type_triangle(self):
        p = Product(sku="TRI", width=300, depth=200, height=150, weight=1000,
                    geometry_type=GeometryType.TRIANGLE,
                    geometry_data=[(0, 0), (300, 0), (0, 200)])
        assert p.geometry_type == GeometryType.TRIANGLE
        assert p.geometry_data is not None

    def test_orientation_constraint(self):
        p = Product(sku="X1", width=100, depth=100, height=100, weight=100,
                    orientation_constraints=OrientationConstraint.UPRIGHT_ONLY)
        assert p.orientation_constraints == OrientationConstraint.UPRIGHT_ONLY


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class TestContainer:
    def test_initial_space_equals_full_volume(self):
        c = Container(name="P1", width=1200, depth=800, height=1500, max_weight=1_000_000)
        assert len(c.spaces) == 1
        assert c.spaces[0] == (0, 0, 0, 1200, 800, 1500)

    def test_items_empty_on_creation(self):
        c = Container(name="P1", width=1200, depth=800, height=1500, max_weight=1_000_000)
        assert c.items == []

    def test_custom_name(self):
        c = Container(name="Pallet-42", width=100, depth=100, height=100, max_weight=100)
        assert c.name == "Pallet-42"


# ---------------------------------------------------------------------------
# PlacedItem
# ---------------------------------------------------------------------------

class TestPlacedItem:
    def _product(self, **kwargs):
        defaults = dict(sku="P", width=100, depth=200, height=300, weight=500)
        defaults.update(kwargs)
        return Product(**defaults)

    def test_rotated_dimensions_use_placed_values(self):
        p = self._product()
        item = PlacedItem(product=p, pos_x=0, pos_y=0, pos_z=0,
                          placed_width=200, placed_depth=100, placed_height=300)
        assert item.rotated_width == 200
        assert item.rotated_depth == 100
        assert item.rotated_height == 300

    def test_rotated_dimensions_fallback_to_product(self):
        p = self._product()
        item = PlacedItem(product=p, pos_x=0, pos_y=0, pos_z=0)
        assert item.rotated_width == 100
        assert item.rotated_depth == 200
        assert item.rotated_height == 300

    def test_weight_delegates_to_product(self):
        p = self._product(weight=9999)
        item = PlacedItem(product=p, pos_x=0, pos_y=0, pos_z=0)
        assert item.weight == 9999

    def test_sku_delegates_to_product(self):
        p = self._product(sku="SKU-1")
        item = PlacedItem(product=p, pos_x=0, pos_y=0, pos_z=0)
        assert item.sku == "SKU-1"

    def test_pair_defaults(self):
        p = self._product()
        item = PlacedItem(product=p, pos_x=0, pos_y=0, pos_z=0)
        assert item.pair_id is None
        assert item.pair_second is False
