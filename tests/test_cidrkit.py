import io
import json
import unittest
from contextlib import redirect_stdout

from cidrkit import contains, exclude, info, merge, range_to_cidrs, split
from cidrkit.cli import main
from cidrkit.core import CidrError


def s(nets):
    return [str(n) for n in nets]


class InfoTests(unittest.TestCase):
    def test_ipv4(self):
        d = info("192.168.10.77/26")
        self.assertEqual(d["network"], "192.168.10.64/26")
        self.assertEqual(d["host"], "192.168.10.77")
        self.assertEqual(d["netmask"], "255.255.255.192")
        self.assertEqual(d["wildcard"], "0.0.0.63")
        self.assertEqual(d["broadcast"], "192.168.10.127")
        self.assertEqual((d["first_usable"], d["last_usable"], d["usable"]), ("192.168.10.65", "192.168.10.126", 62))
        self.assertEqual(d["scope"], "private")
        self.assertEqual(d["class"], "C")

    def test_edge_prefixes(self):
        self.assertEqual(info("10.0.0.0/31")["usable"], 2)
        self.assertEqual(info("10.0.0.5/32")["usable"], 1)
        self.assertEqual(info("100.64.1.0/24")["scope"], "shared (CGNAT)")
        self.assertEqual(info("8.8.8.0/24")["scope"], "public")

    def test_ipv6(self):
        d = info("2001:db8::/48")
        self.assertEqual(d["version"], 6)
        self.assertNotIn("netmask", d)
        self.assertEqual(info("fe80::/64")["scope"], "link-local")

    def test_bad(self):
        with self.assertRaises(CidrError):
            info("10.0.0.0/33")


class OpsTests(unittest.TestCase):
    def test_split_prefix_and_count(self):
        self.assertEqual(s(split("10.0.0.0/24", prefix=26)),
                         ["10.0.0.0/26", "10.0.0.64/26", "10.0.0.128/26", "10.0.0.192/26"])
        self.assertEqual(len(split("10.0.0.0/24", count=3)), 4)  # rounds up to a power of two
        with self.assertRaises(CidrError):
            split("10.0.0.0/24", prefix=20)
        with self.assertRaises(CidrError):
            split("10.0.0.0/8", prefix=32)  # too many

    def test_merge(self):
        self.assertEqual(s(merge(["10.0.0.0/25", "10.0.0.128/25", "10.0.1.0/24", "10.0.0.5/32", "::1/128"])),
                         ["10.0.0.0/23", "::1/128"])

    def test_contains(self):
        self.assertTrue(contains("10.0.0.0/8", "10.20.30.40"))
        self.assertTrue(contains("10.0.0.0/8", "10.1.0.0/16"))
        self.assertFalse(contains("10.0.0.0/16", "10.0.0.0/8"))
        self.assertFalse(contains("10.0.0.0/8", "::1"))

    def test_range(self):
        self.assertEqual(s(range_to_cidrs("10.0.0.5-10.0.0.20")),
                         ["10.0.0.5/32", "10.0.0.6/31", "10.0.0.8/29", "10.0.0.16/30", "10.0.0.20/32"])
        self.assertEqual(s(range_to_cidrs("10.0.0.255-10.0.0.0")), ["10.0.0.0/24"])

    def test_exclude(self):
        self.assertEqual(s(exclude("10.0.0.0/24", ["10.0.0.64/26"])),
                         ["10.0.0.0/26", "10.0.0.128/25"])
        self.assertEqual(s(exclude("10.0.0.0/24", ["10.0.0.0/16"])), [])
        self.assertEqual(s(exclude("10.0.0.0/24", ["192.168.0.0/16"])), ["10.0.0.0/24"])


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(list(argv))
        return code, buf.getvalue()

    def test_contains_exit_code(self):
        self.assertEqual(self.run_cli("contains", "10.0.0.0/8", "10.1.1.1")[0], 0)
        self.assertEqual(self.run_cli("contains", "10.0.0.0/8", "10.1.1.1", "11.0.0.1")[0], 1)

    def test_json_and_error(self):
        code, out = self.run_cli("--json", "split", "10.0.0.0/30", "-p", "31")
        self.assertEqual((code, json.loads(out)), (0, ["10.0.0.0/31", "10.0.0.2/31"]))
        self.assertEqual(self.run_cli("info", "nope")[0], 2)


if __name__ == "__main__":
    unittest.main()
