"""Unit tests for visualizer helper functions (no GUI launched)."""
import importlib.util
import sys
from pathlib import Path
import pytest

# Load src/visualizer.py directly so we never accidentally import the legacy
# root-level visualizer.py that lacks the helper functions.
_vis_path = Path(__file__).parent.parent.parent / "src" / "visualizer.py"
_spec = importlib.util.spec_from_file_location("visualizer", _vis_path)
_vis_mod = importlib.util.module_from_spec(_spec)
sys.modules["visualizer"] = _vis_mod
_spec.loader.exec_module(_vis_mod)

from visualizer import (
    _item_color,
    _parse_position,
    _parse_orientation,
    _is_out_of_bounds,
    _COLOR_NORMAL,
    _COLOR_FRAGILE,
    _COLOR_EXPLOSIVE,
    _COLOR_FLAMMABLE,
    _COLOR_TOXIC,
    _COLOR_RADIOACTIVE,
    _COLOR_CORROSIVE,
    _COLOR_BATTERY,
    _COLOR_HAZARDOUS,
    _COLOR_NO_STACK,
    _COLOR_OOB,
)


# ---------------------------------------------------------------------------
# _item_color
# ---------------------------------------------------------------------------

class TestItemColor:
    def _prod(self, **kwargs):
        defaults = {"hazard_classes": [], "fragile": False, "stackable": True}
        defaults.update(kwargs)
        return defaults

    def test_normal_item_gets_normal_color(self):
        assert _item_color(self._prod(), out_of_bounds=False) == _COLOR_NORMAL

    def test_out_of_bounds_gets_oob_color(self):
        assert _item_color(self._prod(), out_of_bounds=True) == _COLOR_OOB

    def test_explosive_class_1(self):
        assert _item_color(self._prod(hazard_classes=["1.1"]), out_of_bounds=False) == _COLOR_EXPLOSIVE

    def test_flammable_class_3(self):
        assert _item_color(self._prod(hazard_classes=["3"]), out_of_bounds=False) == _COLOR_FLAMMABLE

    def test_flammable_class_2_1(self):
        assert _item_color(self._prod(hazard_classes=["2.1"]), out_of_bounds=False) == _COLOR_FLAMMABLE

    def test_toxic_class_6_1(self):
        assert _item_color(self._prod(hazard_classes=["6.1"]), out_of_bounds=False) == _COLOR_TOXIC

    def test_radioactive_class_7(self):
        assert _item_color(self._prod(hazard_classes=["7"]), out_of_bounds=False) == _COLOR_RADIOACTIVE

    def test_corrosive_class_8(self):
        assert _item_color(self._prod(hazard_classes=["8"]), out_of_bounds=False) == _COLOR_CORROSIVE

    def test_battery_class_9a(self):
        assert _item_color(self._prod(hazard_classes=["9A"]), out_of_bounds=False) == _COLOR_BATTERY

    def test_other_hazard(self):
        assert _item_color(self._prod(hazard_classes=["9"]), out_of_bounds=False) == _COLOR_HAZARDOUS

    def test_fragile_no_hazard(self):
        assert _item_color(self._prod(fragile=True), out_of_bounds=False) == _COLOR_FRAGILE

    def test_non_stackable_no_hazard(self):
        assert _item_color(self._prod(stackable=False), out_of_bounds=False) == _COLOR_NO_STACK

    def test_explosive_takes_priority_over_fragile(self):
        prod = self._prod(hazard_classes=["1.1"], fragile=True)
        assert _item_color(prod, out_of_bounds=False) == _COLOR_EXPLOSIVE

    def test_oob_takes_priority_over_hazard(self):
        prod = self._prod(hazard_classes=["1.1"])
        assert _item_color(prod, out_of_bounds=True) == _COLOR_OOB


# ---------------------------------------------------------------------------
# _parse_position
# ---------------------------------------------------------------------------

class TestParsePosition:
    def test_dict_with_pos_keys(self):
        result = _parse_position({"pos_x": 10, "pos_y": 20, "pos_z": 30})
        assert result == {"pos_x": 10, "pos_y": 20, "pos_z": 30}

    def test_dict_case_insensitive(self):
        result = _parse_position({"POS_X": 10, "POS_Y": 20, "POS_Z": 30})
        assert result == {"pos_x": 10, "pos_y": 20, "pos_z": 30}

    def test_list_format(self):
        result = _parse_position([5, 10, 15])
        assert result == {"pos_x": 5, "pos_y": 10, "pos_z": 15}

    def test_tuple_format(self):
        result = _parse_position((5, 10, 15))
        assert result == {"pos_x": 5, "pos_y": 10, "pos_z": 15}

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_position({"x": 1, "y": 2})


# ---------------------------------------------------------------------------
# _parse_orientation
# ---------------------------------------------------------------------------

class TestParseOrientation:
    def test_dict_with_width_depth_height(self):
        result = _parse_orientation({"width": 100, "depth": 200, "height": 300})
        assert result == {"width": 100, "depth": 200, "height": 300}

    def test_dict_with_w_d_h(self):
        result = _parse_orientation({"w": 100, "d": 200, "h": 300})
        assert result == {"width": 100, "depth": 200, "height": 300}

    def test_list_format(self):
        result = _parse_orientation([100, 200, 300])
        assert result == {"width": 100, "depth": 200, "height": 300}

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            _parse_orientation({"x": 1})


# ---------------------------------------------------------------------------
# _is_out_of_bounds
# ---------------------------------------------------------------------------

class TestIsOutOfBounds:
    def _pos(self, x=0, y=0, z=0):
        return {"pos_x": x, "pos_y": y, "pos_z": z}

    def _size(self, w=100, d=100, h=100):
        return {"width": w, "depth": d, "height": h}

    def test_item_inside_container_is_not_oob(self):
        assert not _is_out_of_bounds(1200, 800, 1500, self._pos(0, 0, 0), self._size(100, 100, 100))

    def test_item_exactly_at_boundary_is_not_oob(self):
        # item from 0 to 1200 exactly fits container width=1200
        assert not _is_out_of_bounds(1200, 800, 1500, self._pos(0, 0, 0), self._size(1200, 800, 1500))

    def test_item_exceeding_x_is_oob(self):
        assert _is_out_of_bounds(1200, 800, 1500, self._pos(1200, 0, 0), self._size(1, 1, 1))

    def test_item_exceeding_y_is_oob(self):
        assert _is_out_of_bounds(1200, 800, 1500, self._pos(0, 800, 0), self._size(1, 1, 1))

    def test_item_exceeding_z_is_oob(self):
        assert _is_out_of_bounds(1200, 800, 1500, self._pos(0, 0, 1500), self._size(1, 1, 1))

    def test_negative_x_is_oob(self):
        assert _is_out_of_bounds(1200, 800, 1500, self._pos(-1, 0, 0), self._size(100, 100, 100))

    def test_item_partially_outside_is_oob(self):
        assert _is_out_of_bounds(1200, 800, 1500, self._pos(1100, 0, 0), self._size(200, 100, 100))
