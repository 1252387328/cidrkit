# cidrkit

Everyday subnet math without opening a browser tab. IPv4 and IPv6, zero dependencies.

```console
$ cidrkit info 192.168.10.77/26
network       192.168.10.64/26
version       4
prefix        26
addresses     64
usable        62
first usable  192.168.10.65
last usable   192.168.10.126
netmask       255.255.255.192
wildcard      0.0.0.63
broadcast     192.168.10.127
class         C
scope         private
host          192.168.10.77
```

## Install

```bash
pip install git+https://github.com/1252387328/cidrkit
```

## Commands

```bash
cidrkit info 10.0.0.0/22 2001:db8::/48        # details for one or more networks
cidrkit split 10.0.0.0/24 -p 26                # four /26s
cidrkit split 10.0.0.0/24 -n 3                 # at least 3 equal parts (-> 4 x /26)
cidrkit merge 10.0.0.0/25 10.0.0.128/25 10.0.1.0/24     # -> 10.0.0.0/23
cat allowlist.txt | cidrkit merge              # dedupe and collapse a list from stdin
cidrkit contains 10.0.0.0/8 10.1.2.3 10.9.0.0/16        # exit 0 only if all are inside
cidrkit range 10.0.0.5-10.0.0.20               # minimal CIDRs covering a range
cidrkit exclude 10.0.0.0/24 10.0.0.64/26       # what is left after carving out a block
```

Add `--json` before the command for machine-readable output:

```bash
cidrkit --json split 10.0.0.0/30 -p 31   # ["10.0.0.0/31", "10.0.0.2/31"]
```

### Notes

- `/31` networks report 2 usable addresses (RFC 3021) and `/32` reports 1.
- `scope` distinguishes private, public, loopback, link-local, multicast, CGNAT (`100.64.0.0/10`) and reserved space.
- `split` refuses to list more than 65 536 subnets at once.

Exit codes: `0` success, `1` `contains` found something outside, `2` invalid input.

## Development

```bash
python -m unittest discover -s tests -v
```

## License

MIT
