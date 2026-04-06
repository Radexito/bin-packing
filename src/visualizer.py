import json
import numpy as np
import pyvista as pv
import logging

PALLET_GAP = 300  # mm spacing between pallets

# Color map by product type (priority order: most dangerous first).
# Colors are (R, G, B) floats in [0, 1].
_COLOR_EXPLOSIVE   = (0.8, 0.0, 0.0)   # dark red   — Class 1
_COLOR_FLAMMABLE   = (1.0, 0.5, 0.0)   # orange     — Class 2.1 / 3 / 4.*
_COLOR_TOXIC       = (0.6, 0.0, 0.8)   # purple     — Class 6
_COLOR_RADIOACTIVE = (0.7, 1.0, 0.0)   # lime       — Class 7
_COLOR_CORROSIVE   = (0.55, 0.27, 0.07)# brown      — Class 8
_COLOR_BATTERY     = (0.0, 0.75, 1.0)  # cyan       — Class 9A
_COLOR_HAZARDOUS   = (1.0, 0.4, 0.6)   # pink       — other hazard
_COLOR_FRAGILE     = (1.0, 1.0, 0.0)   # yellow     — fragile (no hazard class)
_COLOR_NO_STACK    = (0.2, 0.4, 1.0)   # blue       — non-stackable
_COLOR_NORMAL      = (0.45, 0.8, 0.45) # green      — normal
_COLOR_OOB         = (1.0, 0.0, 0.0)   # red        — out-of-bounds violation

_LEGEND_ENTRIES = [
    ["Explosive (Class 1)",        _COLOR_EXPLOSIVE],
    ["Flammable (Class 2.1/3/4)",  _COLOR_FLAMMABLE],
    ["Toxic (Class 6)",            _COLOR_TOXIC],
    ["Radioactive (Class 7)",      _COLOR_RADIOACTIVE],
    ["Corrosive (Class 8)",        _COLOR_CORROSIVE],
    ["Battery (Class 9A)",         _COLOR_BATTERY],
    ["Other hazardous",            _COLOR_HAZARDOUS],
    ["Fragile",                    _COLOR_FRAGILE],
    ["Non-stackable",              _COLOR_NO_STACK],
    ["Normal",                     _COLOR_NORMAL],
    ["Out-of-bounds",              _COLOR_OOB],
]

_FLAMMABLE_CLASSES = {"2.1", "3", "4.1", "4.2", "4.3"}
_EXPLOSIVE_CLASSES = {"1.1", "1.2", "1.3", "1.4", "1.5", "1.6"}
_TOXIC_CLASSES     = {"6.1", "6.2"}


def _item_color(product: dict, out_of_bounds: bool) -> tuple:
    """Return a display color for a product based on its properties."""
    if out_of_bounds:
        return _COLOR_OOB

    hazard = set(product.get("hazard_classes") or [])

    if hazard & _EXPLOSIVE_CLASSES:
        return _COLOR_EXPLOSIVE
    if hazard & _FLAMMABLE_CLASSES:
        return _COLOR_FLAMMABLE
    if hazard & _TOXIC_CLASSES:
        return _COLOR_TOXIC
    if "7" in hazard:
        return _COLOR_RADIOACTIVE
    if "8" in hazard:
        return _COLOR_CORROSIVE
    if "9A" in hazard:
        return _COLOR_BATTERY
    if hazard:
        return _COLOR_HAZARDOUS
    if product.get("fragile"):
        return _COLOR_FRAGILE
    if not product.get("stackable", True):
        return _COLOR_NO_STACK
    return _COLOR_NORMAL


def load_packing(path: str):
    with open(path, "r") as f:
        return json.load(f)


def _parse_position(pos):
    if isinstance(pos, dict):
        pl = {k.lower(): v for k, v in pos.items()}
        if {"pos_x", "pos_y", "pos_z"}.issubset(pl.keys()):
            return {"pos_x": pl["pos_x"], "pos_y": pl["pos_y"], "pos_z": pl["pos_z"]}
    elif isinstance(pos, (list, tuple)) and len(pos) >= 3:
        return {"pos_x": pos[0], "pos_y": pos[1], "pos_z": pos[2]}
    raise ValueError(f"Unsupported position format {pos}")


def _parse_orientation(o):
    if isinstance(o, dict):
        ol = {k.lower(): v for k, v in o.items()}
        if {"width", "depth", "height"}.issubset(ol.keys()):
            return {"width": ol["width"], "depth": ol["depth"], "height": ol["height"]}
        if {"w", "d", "h"}.issubset(ol.keys()):
            return {"width": ol["w"], "depth": ol["d"], "height": ol["h"]}
    elif isinstance(o, (list, tuple)) and len(o) >= 3:
        return {"width": o[0], "depth": o[1], "height": o[2]}
    raise ValueError("Unsupported orientation format")


def _is_out_of_bounds(pw, pd, ph, pos, size):
    x, y, z = pos["pos_x"], pos["pos_y"], pos["pos_z"]
    w, d, h = size["width"], size["depth"], size["height"]
    return x < 0 or y < 0 or z < 0 or x + w > pw or y + d > pd or z + h > ph


def _make_item_mesh(ox, oy, oz, w, d, h, product: dict) -> pv.PolyData:
    """Return a PyVista mesh for one item.

    For TRIANGLE / POLYGON geometry types with valid geometry_data, renders
    an extruded prism matching the actual footprint shape.
    Falls back to a box for RECTANGLE, CUSTOM, or missing geometry_data.
    """
    geo_type = product.get("geometry_type", "RECTANGLE")
    geo_data = product.get("geometry_data")

    if geo_type in ("TRIANGLE", "POLYGON") and geo_data and len(geo_data) >= 3:
        try:
            pts_2d = [(float(p[0]), float(p[1])) for p in geo_data]
            # Compute bounding box so the footprint is offset to (ox, oy)
            min_x = min(p[0] for p in pts_2d)
            min_y = min(p[1] for p in pts_2d)
            n = len(pts_2d)

            bottom = np.array([[ox + p[0] - min_x, oy + p[1] - min_y, oz]        for p in pts_2d])
            top    = np.array([[ox + p[0] - min_x, oy + p[1] - min_y, oz + h]    for p in pts_2d])
            points = np.vstack([bottom, top])

            faces = []
            # Bottom cap (reverse winding)
            faces += [n] + list(reversed(range(n)))
            # Top cap
            faces += [n] + list(range(n, 2 * n))
            # Side quads
            for i in range(n):
                j = (i + 1) % n
                faces += [4, i, j, j + n, i + n]

            return pv.PolyData(points, np.array(faces))
        except Exception as e:
            logging.warning("Could not build polygon mesh for %s: %s", product.get("sku"), e)

    # Default: axis-aligned box
    return pv.Cube(
        center=(ox + w / 2, oy + d / 2, oz + h / 2),
        x_length=w, y_length=d, z_length=h,
    )



def visualize(path="packing_result.json"):
    data = load_packing(path)
    plotter = pv.Plotter()
    plotter.show_axes()
    plotter.set_background("white")

    violations = []

    for pallet_index, pallet in enumerate(data.get("pallets", [])):
        pw = pallet["dimensions"]["width"]
        pd = pallet["dimensions"]["depth"]
        ph = pallet["dimensions"]["height"]
        pallet_offset_x = pallet_index * (pw + PALLET_GAP)

        # Pallet boundary wireframe
        pallet_cube = pv.Cube(
            center=(pallet_offset_x + pw / 2, pd / 2, ph / 2),
            x_length=pw, y_length=pd, z_length=ph,
        )
        plotter.add_mesh(pallet_cube, style="wireframe", color="black", line_width=2)

        for item in pallet.get("items", []):
            try:
                pos  = _parse_position(item["position"])
                size = _parse_orientation(item.get("placed_dimensions", item.get("orientation", item.get("size", {}))))
            except Exception as e:
                logging.warning("Skipping item: %s", e)
                continue

            oob = _is_out_of_bounds(pw, pd, ph, pos, size)
            if oob:
                violations.append({"pallet": pallet_index, "item": item.get("product", {}).get("sku"), "pos": pos, "size": size})

            color = _item_color(item.get("product", {}), oob)
            mesh = _make_item_mesh(
                pallet_offset_x + pos["pos_x"], pos["pos_y"], pos["pos_z"],
                size["width"], size["depth"], size["height"],
                item.get("product", {}),
            )
            plotter.add_mesh(mesh, color=color, opacity=0.85, show_edges=True)

    if violations:
        logging.error("Detected %d out-of-bounds items", len(violations))

    # Legend — only show entries that actually appear in the data
    used_colors = set()
    for pallet in data.get("pallets", []):
        for item in pallet.get("items", []):
            prod = item.get("product", {})
            oob = False  # legend uses type, not OOB
            used_colors.add(_item_color(prod, oob))
    if violations:
        used_colors.add(_COLOR_OOB)

    legend = [entry for entry in _LEGEND_ENTRIES if tuple(entry[1]) in used_colors]
    if legend:
        plotter.add_legend(legend, bcolor="white", border=True, size=(0.2, 0.4))

    plotter.show()


if __name__ == "__main__":
    visualize()

