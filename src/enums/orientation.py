"""Orientation constraint definitions for products."""
from enum import Enum


class OrientationConstraint(str, Enum):
    """Allowed orientation constraints for a product during packing.

    When set, takes precedence over the ``allow_rotations`` flag.

    Values
    ------
    UPRIGHT_ONLY
        The item must be placed exactly as defined — no rotation of any kind.
        Use for liquids, items with "this side up" labelling, or any product
        whose top/bottom surface must not change.
    NO_LAY_FLAT
        The item may rotate 90 ° around the vertical (Z) axis — i.e. width
        and depth may be swapped — but it cannot be tipped onto its side or
        stood on its end.  Height always remains the height.
        Use for tall boxes, monitors, or items that must remain upright but
        can face any horizontal direction.
    """

    UPRIGHT_ONLY = "upright_only"
    NO_LAY_FLAT  = "no_lay_flat"
