"""Standalone PlanoVision feasibility validation service."""

from itertools import combinations

from . import feasibility_core
from . import validation_helpers
from .data_loader import load_feasibility_data


def create_validator():
    """Configure the extracted validator with simulation evidence."""

    availability, collaboration = load_feasibility_data()

    dependencies = {
        "combinations": combinations,
        "availability": availability,
        "collaboration": collaboration,
        "validate_service_option_lkr":
            validation_helpers.validate_service_option_lkr,
        "validate_vendor_availability":
            validation_helpers.validate_vendor_availability,
        "validate_vendor_collaboration":
            validation_helpers.validate_vendor_collaboration,
    }

    for name, value in dependencies.items():
        setattr(feasibility_core, name, value)

    return feasibility_core.validate_package_feasibility


def validate_package(event, package_options):
    """Validate a package using synthetic simulation evidence."""

    validator = create_validator()
    return validator(event, package_options)
