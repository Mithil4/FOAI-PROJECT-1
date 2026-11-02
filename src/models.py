"""
Models and Data Structures for Smart Package Management System.
Defines Package, Locker, and CSP Constraint representations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class SizeCategory(str, Enum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"

    @classmethod
    def fits(cls, package_size: "SizeCategory", locker_size: "SizeCategory") -> bool:
        hierarchy = {cls.SMALL: 1, cls.MEDIUM: 2, cls.LARGE: 3}
        return hierarchy[package_size] <= hierarchy[locker_size]


class PriorityLevel(str, Enum):
    STANDARD = "Standard"
    EXPRESS = "Express"
    URGENT = "Urgent"


@dataclass
class Package:
    """Represents a delivery package requiring storage/locker assignment."""
    id: str
    tracking_number: str
    recipient_name: str
    size: SizeCategory
    weight_kg: float
    is_perishable: bool = False
    priority: PriorityLevel = PriorityLevel.STANDARD
    assigned_locker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ID": self.id,
            "Tracking #": self.tracking_number,
            "Recipient": self.recipient_name,
            "Size": self.size.value,
            "Weight (kg)": self.weight_kg,
            "Perishable": "Yes" if self.is_perishable else "No",
            "Priority": self.priority.value,
            "Assigned Locker": self.assigned_locker_id or "Unassigned"
        }


@dataclass
class Locker:
    """Represents a physical compartment in the smart locker facility."""
    id: str
    compartment_number: int
    size: SizeCategory
    max_weight_kg: float
    is_refrigerated: bool = False
    accessibility_tier: int = 1  # 1 = Eye level / easily accessible, 2 = Upper/Lower
    current_package_id: Optional[str] = None

    @property
    def is_occupied(self) -> bool:
        return self.current_package_id is not None

    def can_accommodate(self, package: Package) -> bool:
        """Checks unary physical constraints without considering occupation."""
        # Size fit check
        if not SizeCategory.fits(package.size, self.size):
            return False
        # Weight check
        if package.weight_kg > self.max_weight_kg:
            return False
        # Temperature check: if perishable, must be refrigerated
        if package.is_perishable and not self.is_refrigerated:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Locker ID": self.id,
            "Comp #": self.compartment_number,
            "Size": self.size.value,
            "Max Weight (kg)": self.max_weight_kg,
            "Refrigerated": "Yes" if self.is_refrigerated else "No",
            "Tier": f"Tier {self.accessibility_tier}",
            "Status": "Occupied" if self.is_occupied else "Available",
            "Package ID": self.current_package_id or "-"
        }

