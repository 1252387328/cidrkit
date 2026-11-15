"""cidrkit - everyday subnet math on the command line."""

from .core import info, split, merge, contains, range_to_cidrs, exclude, parse_network

__all__ = ["info", "split", "merge", "contains", "range_to_cidrs", "exclude", "parse_network"]
__version__ = "0.1.0"
