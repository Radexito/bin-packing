"""UN Dangerous Goods hazard classification (classes 1–9 with sub-classes)."""
from enum import Enum


class HazardClass(str, Enum):
    """UN Dangerous Goods classes and sub-classes.

    String values match the official UN designation (e.g. "2.1", "6.1").
    A product may carry multiple hazard classes simultaneously.

    References: UN Model Regulations (Orange Book), IATA DGR, IMDG Code.
    """

    # Class 1 — Explosives
    CLASS_1_1 = "1.1"  # Mass explosion hazard
    CLASS_1_2 = "1.2"  # Projection hazard, not mass explosion
    CLASS_1_3 = "1.3"  # Fire hazard and minor blast/projection hazard
    CLASS_1_4 = "1.4"  # No significant hazard (consumer fireworks, etc.)
    CLASS_1_5 = "1.5"  # Very insensitive, mass explosion hazard
    CLASS_1_6 = "1.6"  # Extremely insensitive, no mass explosion hazard

    # Class 2 — Gases
    CLASS_2_1 = "2.1"  # Flammable gas (e.g. propane, hydrogen)
    CLASS_2_2 = "2.2"  # Non-flammable, non-toxic gas (e.g. nitrogen, CO2)
    CLASS_2_3 = "2.3"  # Toxic gas (e.g. chlorine, ammonia)

    # Class 3 — Flammable Liquids
    CLASS_3 = "3"  # Flammable liquid (e.g. petrol, acetone, paint)

    # Class 4 — Flammable Solids / Reactive
    CLASS_4_1 = "4.1"  # Flammable solid (e.g. matches, sulphur)
    CLASS_4_2 = "4.2"  # Spontaneously combustible (e.g. white phosphorus)
    CLASS_4_3 = "4.3"  # Dangerous when wet / emits flammable gas (e.g. sodium)

    # Class 5 — Oxidising Substances and Organic Peroxides
    CLASS_5_1 = "5.1"  # Oxidiser (e.g. hydrogen peroxide, ammonium nitrate)
    CLASS_5_2 = "5.2"  # Organic peroxide (e.g. benzoyl peroxide)

    # Class 6 — Toxic and Infectious Substances
    CLASS_6_1 = "6.1"  # Toxic substance (e.g. pesticides, cyanides)
    CLASS_6_2 = "6.2"  # Infectious substance (e.g. medical/clinical waste, cultures)

    # Class 7 — Radioactive Material
    CLASS_7 = "7"  # Radioactive material (all categories I, II, III)

    # Class 8 — Corrosives
    CLASS_8 = "8"  # Corrosive substance (e.g. acids, batteries acid, caustic soda)

    # Class 9 — Miscellaneous Dangerous Goods
    CLASS_9 = "9"    # Misc dangerous goods (e.g. dry ice, magnetised material)
    CLASS_9A = "9A"  # Lithium batteries (UN 3480 / 3481 / 3090 / 3091)

    # ------------------------------------------------------------------ helpers

    @property
    def primary_class(self) -> int:
        """Return the top-level UN class number (1–9)."""
        return int(self.value.rstrip("A")[0])

    @property
    def is_flammable(self) -> bool:
        """Return True for classes that are flammable by UN definition."""
        return self in {
            HazardClass.CLASS_2_1,
            HazardClass.CLASS_3,
            HazardClass.CLASS_4_1,
            HazardClass.CLASS_4_2,
            HazardClass.CLASS_4_3,
        }

    @property
    def requires_segregation(self) -> bool:
        """Return True for classes that require segregation from incompatible goods."""
        return self.primary_class in {1, 2, 3, 4, 5, 6, 7, 8}
