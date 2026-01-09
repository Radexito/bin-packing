import json
import random
import pyvista as pv
import numpy as np

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


def rotate_points(points, rot_x, rot_y, rot_z):
    """Rotate points around the X, Y, and Z axes."""
    # Create rotation matrices for each axis
    rotation_x = np.array([
        [1, 0, 0],
        [0, np.cos(np.radians(rot_x)), -np.sin(np.radians(rot_x))],
        [0, np.sin(np.radians(rot_x)), np.cos(np.radians(rot_x))]
    ])

    rotation_y = np.array([
        [np.cos(np.radians(rot_y)), 0, np.sin(np.radians(rot_y))],
        [0, 1, 0],
        [-np.sin(np.radians(rot_y)), 0, np.cos(np.radians(rot_y))]
    ])

    rotation_z = np.array([
        [np.cos(np.radians(rot_z)), -np.sin(np.radians(rot_z)), 0],
        [np.sin(np.radians(rot_z)), np.cos(np.radians(rot_z)), 0],
        [0, 0, 1]
    ])

    # Apply rotation to the points
    rotation_matrix = rotation_z @ rotation_y @ rotation_x
    return np.dot(points, rotation_matrix.T)


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
            rot_x = item["rotation"]["rot_x"]
            rot_y = item["rotation"]["rot_y"]
            rot_z = item["rotation"]["rot_z"]

            # Set up the corners of the bounding box (box corners)
            corners = np.array([
                [-size["width"] / 2, -size["depth"] / 2, -size["height"] / 2],
                [size["width"] / 2, -size["depth"] / 2, -size["height"] / 2],
                [size["width"] / 2, size["depth"] / 2, -size["height"] / 2],
                [-size["width"] / 2, size["depth"] / 2, -size["height"] / 2],
                [-size["width"] / 2, -size["depth"] / 2, size["height"] / 2],
                [size["width"] / 2, -size["depth"] / 2, size["height"] / 2],
                [size["width"] / 2, size["depth"] / 2, size["height"] / 2],
                [-size["width"] / 2, size["depth"] / 2, size["height"] / 2],
            ])

            # Rotate the corners based on the rotations
            rotated_corners = rotate_points(corners, rot_x, rot_y, rot_z)

            # Log the rotated corners for debugging
            print(f"Rotated corners for {item['product']['sku']}: {rotated_corners}")

            # Translate the corners to the correct position
            rotated_corners += np.array([pos["pos_x"], pos["pos_y"], pos["pos_z"]])

            # Log the translated corners to verify position
            print(f"Translated corners for {item['product']['sku']}: {rotated_corners}")

            # Create a polydata from the corners
            item_mesh = pv.PolyData(rotated_corners)

            # Define the 12 edges (lines) for the cube
            item_mesh.lines = [
                [0, 1], [1, 2], [2, 3], [3, 0],  # Bottom face
                [4, 5], [5, 6], [6, 7], [7, 4],  # Top face
                [0, 4], [1, 5], [2, 6], [3, 7], [3, 7]   # Vertical lines
            ]

            # Log lines connectivity
            print(f"Lines connectivity for {item['product']['sku']}: {item_mesh.lines}")

            # Check for the correct number of lines (should be 12 for a cube)
            if len(item_mesh.lines) != 12:
                print(f"Error: Incorrect number of lines for {item['product']['sku']}: {len(item_mesh.lines)}")

            plotter.add_mesh(
                item_mesh,
                color=random_color(),
                opacity=0.85,
                show_edges=True,
            )

    plotter.show()


if __name__ == "__main__":
    visualize()
