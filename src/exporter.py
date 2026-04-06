"""Export containers to JSON."""
import json
from pathlib import Path
import logging
from typing import List

from models.container import Container

logger = logging.getLogger(__name__)

def export_to_json(pallets: List[Container], path: str) -> None:
    """Export packed pallets to JSON."""
    data = {"pallets": []}

    # Iterate through the pallets and serialize the data
    for pallet in pallets:
        pallet_data = {
            "name": pallet.name,
            "dimensions": {
                "width": pallet.width,
                "depth": pallet.depth,
                "height": pallet.height,
            },
            "items": []
        }

        # Iterate through each placed item in the pallet
        for item in pallet.items:
            item_data = {
                "product": item.product.model_dump(mode="json"),  # Serialize the product
                "position": {
                    "pos_x": item.pos_x,
                    "pos_y": item.pos_y,
                    "pos_z": item.pos_z,
                },
                "placed_dimensions": {
                    "width": item.rotated_width,
                    "depth": item.rotated_depth,
                    "height": item.rotated_height,
                },
            }
            pallet_data["items"].append(item_data)

        # Append the pallet data to the main data
        data["pallets"].append(pallet_data)

    # Write the data to a JSON file
    Path(path).write_text(json.dumps(data, indent=2))
    logger.info("Exported packing result to %s", path)
