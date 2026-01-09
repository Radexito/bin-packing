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

    for pallet in pallets:
        data["pallets"].append({
            "name": pallet.name,
            "dimensions": {
                "width": pallet.width,
                "depth": pallet.depth,
                "height": pallet.height,
            },
            "items": [
                {
                    "product": item.product.model_dump(mode="json"),
                    "position": {"x": item.x, "y": item.y, "z": item.z},
                    "orientation": {"width": item.width, "depth": item.depth, "height": item.height},
                }
                for item in pallet.items
            ],
        })

    Path(path).write_text(json.dumps(data, indent=2))
    logger.info("Exported packing result to %s", path)
