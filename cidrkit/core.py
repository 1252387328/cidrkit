"""Subnet operations built on the standard library ``ipaddress`` module."""

from __future__ import annotations

import ipaddress
from typing import Iterable, Union

Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
Address = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class CidrError(ValueError):
    pass


def parse_network(text: str, strict: bool = False) -> Network:
    """Parse '10.0.0.0/24', '10.0.0.7/24' (host bits allowed unless strict), a bare IP, or
    '192.168.1.0/255.255.255.0'."""
    try:
        return ipaddress.ip_network(text.strip(), strict=strict)
    except ValueError as exc:
        raise CidrError(f"invalid network {text!r}: {exc}") from None


def parse_address(text: str) -> Address:
    try:
        return ipaddress.ip_address(text.strip())
    except ValueError as exc:
        raise CidrError(f"invalid address {text!r}: {exc}") from None


def _usable(net: Network) -> tuple[Address | None, Address | None, int]:
    if net.version == 4 and net.prefixlen <= 30:
        return net.network_address + 1, net.broadcast_address - 1, net.num_addresses - 2
    if net.version == 4 and net.prefixlen == 31:  # RFC 3021 point-to-point
        return net.network_address, net.broadcast_address, 2
    return net.network_address, net.broadcast_address, net.num_addresses


def info(text: str) -> dict:
    """Describe a network. If host bits are set, the given address is reported too."""
    net = parse_network(text)
    first, last, usable = _usable(net)
    out = {
        "input": text.strip(),
        "network": str(net),
        "version": net.version,
        "prefix": net.prefixlen,
        "addresses": net.num_addresses,
        "usable": usable,
        "first_usable": str(first),
        "last_usable": str(last),
    }
    if net.version == 4:
        out.update({
            "netmask": str(net.netmask),
            "wildcard": str(net.hostmask),
            "broadcast": str(net.broadcast_address),
            "class": _ipv4_class(net.network_address),
        })
    out["scope"] = _scope(net)
    if "/" in text:
        host = text.strip().split("/")[0]
        if parse_address(host) != net.network_address:
            out["host"] = host
    return out


def _ipv4_class(addr: ipaddress.IPv4Address) -> str:
    first = int(addr) >> 24
    for limit, name in ((128, "A"), (192, "B"), (224, "C"), (240, "D (multicast)")):
        if first < limit:
            return name
    return "E (reserved)"


def _scope(net: Network) -> str:
    if net.is_loopback:
        return "loopback"
    if net.is_link_local:
        return "link-local"
    if net.is_multicast:
        return "multicast"
    if net.version == 4 and net.subnet_of(ipaddress.ip_network("100.64.0.0/10")):
        return "shared (CGNAT)"
    if net.is_private:
        return "private"
    if net.is_reserved or net.is_unspecified:
        return "reserved"
    return "public"


def split(text: str, *, prefix: int | None = None, count: int | None = None) -> list[Network]:
    """Split a network into subnets of a new prefix, or into at least ``count`` equal parts."""
    net = parse_network(text, strict=False)
    max_len = net.max_prefixlen
    if (prefix is None) == (count is None):
        raise CidrError("give exactly one of prefix or count")
    if count is not None:
        if count < 1:
            raise CidrError("count must be >= 1")
        extra = (count - 1).bit_length()
        prefix = net.prefixlen + extra
    assert prefix is not None
    if not net.prefixlen <= prefix <= max_len:
        raise CidrError(f"new prefix /{prefix} must be between /{net.prefixlen} and /{max_len}")
    if prefix - net.prefixlen > 16:
        raise CidrError(f"refusing to list 2^{prefix - net.prefixlen} subnets; use a smaller split")
    return list(net.subnets(new_prefix=prefix))


def merge(texts: Iterable[str]) -> list[Network]:
    """Collapse overlapping and adjacent networks into the smallest list of CIDRs."""
    nets = [parse_network(t) for t in texts]
    out: list[Network] = []
    for version in (4, 6):
        same = [n for n in nets if n.version == version]
        out.extend(ipaddress.collapse_addresses(same))
    return out


def contains(outer: str, inner: str) -> bool:
    """Is an address or network inside ``outer``?"""
    net = parse_network(outer)
    if "/" in inner:
        sub = parse_network(inner)
        return sub.version == net.version and sub.subnet_of(net)
    addr = parse_address(inner)
    return addr.version == net.version and addr in net


def range_to_cidrs(text: str) -> list[Network]:
    """'10.0.0.5-10.0.0.20' -> minimal list of CIDRs covering exactly that range."""
    if "-" not in text:
        raise CidrError("range must look like FIRST-LAST")
    a, b = (parse_address(x) for x in text.split("-", 1))
    if a.version != b.version:
        raise CidrError("range mixes IPv4 and IPv6")
    if a > b:
        a, b = b, a
    return list(ipaddress.summarize_address_range(a, b))


def exclude(base: str, holes: Iterable[str]) -> list[Network]:
    """Remove ``holes`` from ``base`` and return what is left."""
    remaining = [parse_network(base)]
    for h in holes:
        hole = parse_network(h)
        nxt: list[Network] = []
        for net in remaining:
            if hole.version != net.version or not net.overlaps(hole):
                nxt.append(net)
            elif hole.supernet_of(net):
                continue
            else:
                nxt.extend(net.address_exclude(hole))
        remaining = nxt
    return sorted(remaining, key=lambda n: (n.version, n.network_address))
