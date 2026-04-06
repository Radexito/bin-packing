"""Geometry type enum for product footprint shapes."""
from enum import Enum


class GeometryType(str, Enum):
    RECTANGLE = "RECTANGLE"
    TRIANGLE  = "TRIANGLE"
    POLYGON   = "POLYGON"
    CUSTOM    = "CUSTOM"
