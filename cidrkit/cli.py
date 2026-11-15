"""cidrkit CLI."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .core import CidrError, contains, exclude, info, merge, range_to_cidrs, split


def _read_many(values: list[str]) -> list[str]:
    """Positional values, or one per line from stdin when none are given / '-' is used."""
    if not values or values == ["-"]:
        return [line.split("#", 1)[0].strip() for line in sys.stdin if line.split("#", 1)[0].strip()]
    return values


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cidrkit", description="Everyday subnet math.")
    p.add_argument("-V", "--version", action="version", version=f"cidrkit {__version__}")
    p.add_argument("--json", action="store_true", help="JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("info", help="describe a network or host/prefix")
    s.add_argument("network", nargs="+")

    s = sub.add_parser("split", help="split into smaller subnets")
    s.add_argument("network")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("-p", "--prefix", type=int, help="new prefix length, e.g. 26")
    g.add_argument("-n", "--count", type=int, help="at least this many equal parts")

    s = sub.add_parser("merge", help="collapse overlapping/adjacent networks (reads stdin if none given)")
    s.add_argument("networks", nargs="*")

    s = sub.add_parser("contains", help="exit 0 if every item is inside NETWORK")
    s.add_argument("network")
    s.add_argument("items", nargs="+", help="addresses or networks")

    s = sub.add_parser("range", help="convert FIRST-LAST into CIDRs")
    s.add_argument("range")

    s = sub.add_parser("exclude", help="remove subnets from a network")
    s.add_argument("network")
    s.add_argument("holes", nargs="+")
    return p


def _print_nets(nets, as_json: bool) -> None:
    if as_json:
        print(json.dumps([str(n) for n in nets]))
    else:
        for n in nets:
            print(n)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "info":
            rows = [info(n) for n in args.network]
            if args.json:
                print(json.dumps(rows if len(rows) > 1 else rows[0], indent=2))
            else:
                for i, row in enumerate(rows):
                    if i:
                        print()
                    width = max(len(k) for k in row)
                    for k, v in row.items():
                        if k == "input":
                            continue
                        label = k.replace("_", " ")
                        print(f"{label:<{width}}  {v:,}" if isinstance(v, int) and k != "version" and k != "prefix"
                              else f"{label:<{width}}  {v}")
        elif args.cmd == "split":
            _print_nets(split(args.network, prefix=args.prefix, count=args.count), args.json)
        elif args.cmd == "merge":
            _print_nets(merge(_read_many(args.networks)), args.json)
        elif args.cmd == "contains":
            results = {item: contains(args.network, item) for item in args.items}
            if args.json:
                print(json.dumps(results))
            else:
                for item, ok in results.items():
                    print(f"{'yes' if ok else 'no ':<3}  {item}")
            return 0 if all(results.values()) else 1
        elif args.cmd == "range":
            _print_nets(range_to_cidrs(args.range), args.json)
        elif args.cmd == "exclude":
            _print_nets(exclude(args.network, args.holes), args.json)
    except CidrError as exc:
        print(f"cidrkit: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
