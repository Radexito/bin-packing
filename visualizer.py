import json
import random
import pyvista as pv

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


def visualize(path="packing_result.json"):
    data = load_packing(path)

    plotter = pv.Plotter()
    plotter.show_axes()
    plotter.set_background("white")

    for pallet_index, pallet in enumerate(data["pallets"]):
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
        for item in pallet["items"]:
            pos = item["position"]
            size = item["orientation"]

            cube = pv.Cube(
                center=(
                    pallet_offset_x + pos["x"] + size["width"] / 2,
                    pos["y"] + size["depth"] / 2,
                    pos["z"] + size["height"] / 2,
                ),
                x_length=size["width"],
                y_length=size["depth"],
                z_length=size["height"],
            )

            plotter.add_mesh(
                cube,
                color=random_color(),
                opacity=0.85,
                show_edges=True,
            )

    plotter.show()


if __name__ == "__main__":
    visualize()
