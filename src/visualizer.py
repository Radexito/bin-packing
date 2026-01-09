import json
import random
import pyvista as pv
import logging

PALLET_GAP = 300  # mm spacing between pallets


def load_packing(path: str):
    with open(path, "r") as f:
        return json.load(f)


def random_color():
    return (
        random.random(),
        random.random(),
        random.random(),
    )


def _parse_position(pos):
    """Return dict with keys x,y,z from list/tuple or dict."""
    if isinstance(pos, dict):
        # accept direct keys 'x','y','z' (case-insensitive)
        pl = {k.lower(): v for k, v in pos.items()}
        if {"pos_x", "pos_y", "pos_z"}.issubset(pl.keys()):
            return {"pos_x": pl["pos_x"], "pos_y": pl["pos_y"], "pos_z": pl["pos_z"]}
        # fallthrough to try numeric sequence values if present as values
    elif isinstance(pos, (list, tuple)) and len(pos) >= 3:
        return {"pos_x": pos[0], "pos_y": pos[1], "pos_z": pos[2]}
    raise ValueError(f"Unsupported position format {pos}")


def _parse_orientation(o):
    """Return dict with keys width,depth,height from dict or sequence."""
    if isinstance(o, dict):
        ol = {k.lower(): v for k, v in o.items()}
        if {"width", "depth", "height"}.issubset(ol.keys()):
            return {"width": ol["width"], "depth": ol["depth"], "height": ol["height"]}
        # try short keys
        if {"w", "d", "h"}.issubset(ol.keys()):
            return {"width": ol["w"], "depth": ol["d"], "height": ol["h"]}
    elif isinstance(o, (list, tuple)) and len(o) >= 3:
        return {"width": o[0], "depth": o[1], "height": o[2]}
    raise ValueError("Unsupported orientation format")


def _is_out_of_bounds(pw, pd, ph, pos, size):
    """Return True if item at pos with size extends outside pallet dimensions."""
    x, y, z = pos["pos_x"], pos["pos_y"], pos["pos_z"]
    w, d, h = size["width"], size["depth"], size["height"]
    if x < 0 or y < 0 or z < 0:
        return True
    if x + w > pw or y + d > pd or z + h > ph:
        return True
    return False


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

        # Offset pallets along X axis
        pallet_offset_x = pallet_index * (pw + PALLET_GAP)

        # Draw pallet boundary (wireframe)
        pallet_cube = pv.Cube(
            center=(
                pallet_offset_x + pw / 2,
                pd / 2,
                ph / 2,
            ),
            x_length=pw,
            y_length=pd,
            z_length=ph,
        )
        plotter.add_mesh(
            pallet_cube,
            style="wireframe",
            color="black",
            line_width=2,
        )

        # Draw placed items
        for item in pallet.get("items", []):
            try:
                pos = _parse_position(item["position"])
                size = _parse_orientation(item.get("orientation", item.get("size", {})))
            except Exception as e:
                logging.warning("Skipping item due to parse error: %s (%s)", item.get("id", item.get("name")), e)
                continue

            out_of_bounds = _is_out_of_bounds(pw, pd, ph, pos, size)
            if out_of_bounds:
                violations.append({
                    "pallet": pallet_index,
                    "item": item.get("id", item.get("name", item.get("sku"))),
                    "pos": pos,
                    "size": size,
                })

            cube = pv.Cube(
                center=(
                    pallet_offset_x + pos["pos_x"] + size["width"] / 2,
                    pos["pos_y"] + size["depth"] / 2,
                    pos["pos_z"] + size["height"] / 2,
                ),
                x_length=size["width"],
                y_length=size["depth"],
                z_length=size["height"],
            )

            plotter.add_mesh(
                cube,
                color=(1.0, 0.0, 0.0) if out_of_bounds else random_color(),
                opacity=0.85,
                show_edges=True,
            )

    if violations:
        logging.error("Detected %d out-of-bounds items:", len(violations))
        for v in violations:
            logging.error("Pallet %s item %s pos=%s size=%s", v["pallet"], v["item"], v["pos"], v["size"])

    plotter.show()


if __name__ == "__main__":
    visualize()
