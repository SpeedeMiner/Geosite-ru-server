import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from project_geosite import (FULL, ROOT, REQUIRED_ROOTS, coverage_losses,
                             digest, encode, message, project, read_ru)


def rule(typ, name):
    return bytes([8, typ]) + message(2, name.encode())


def fixture(extra):
    ru = {(ROOT, name): rule(ROOT, name) for name in REQUIRED_ROOTS}
    ru.update({key: rule(*key) for key in extra})
    block = message(1, message(1, b"BLOCK") + message(2, rule(ROOT, "blocked.example")))
    hydra = message(1, message(1, b"HYDRA") + message(2, rule(ROOT, "hydra.example")))
    return encode(ru) + block + hydra


class ProjectionTest(unittest.TestCase):
    def test_only_ru_and_exact_hosts_keep_type_and_bytes(self):
        host = FULL, "seller.ozon.am"
        incoming = fixture({host, (ROOT, "example.com")})
        output, source_rules, target_rules = project(incoming, {"private.test"}, {"legacy"})
        self.assertEqual(read_ru(output)[0], {"RU"})
        self.assertEqual(target_rules[host], source_rules[host])
        self.assertNotIn((ROOT, host[1]), target_rules)
        self.assertNotIn((ROOT, "blocked.example"), target_rules)
        self.assertNotIn((ROOT, "hydra.example"), target_rules)
        self.assertIn((ROOT, "legacy"), target_rules)

    def test_exclusions_cover_descendants_and_suffix_ancestors(self):
        _, _, rules = project(fixture({
            (ROOT, "4pda.to"), (ROOT, "to"), (FULL, "forum.4pda.to"),
            (ROOT, "not4pda.to"), (FULL, "to"),
            (ROOT, "42.168.192.in-addr.arpa"), (ROOT, "in-addr.arpa"),
            (ROOT, "arpa"), (FULL, "sub.routerlogin.com"),
        }), {"4pda.to", "in-addr.arpa", "routerlogin.com"}, set())
        self.assertEqual(set(rules) - {(ROOT, n) for n in REQUIRED_ROOTS},
                         {(ROOT, "not4pda.to"), (FULL, "to")})

    def test_pruning_does_not_turn_full_into_suffix(self):
        _, _, rules = project(fixture({
            (ROOT, "service.net"), (FULL, "api.service.net"),
            (FULL, "service.net"), (FULL, "exact.net"), (FULL, "child.exact.net"),
        }), {"private.test"}, set())
        self.assertEqual(set(rules) - {(ROOT, n) for n in REQUIRED_ROOTS},
                         {(ROOT, "service.net"), (FULL, "exact.net"), (FULL, "child.exact.net")})

    def test_rejects_duplicate_category_and_malformed_wire_data(self):
        source = fixture({(FULL, "exact.net")})
        for bad in (source + source, source[:-1], b"\x00", b"\x0a\x05abc"):
            with self.subTest(bad=bad[:16]), self.assertRaises(ValueError):
                read_ru(bad)

    def test_rejects_attributes_and_unsupported_match_types(self):
        for payload in (rule(ROOT, "bad.net") + message(3, b""), rule(1, "bad.net")):
            db = message(1, message(1, b"RU") + message(2, payload))
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                read_ru(db)

    def test_rejects_missing_required_roots_and_conflicting_retain_rule(self):
        with self.assertRaises(ValueError):
            project(encode({(ROOT, "ru"): rule(ROOT, "ru")}), {"private.test"}, set())
        with self.assertRaises(ValueError):
            project(fixture(set()), {"router.net"}, {"net"})

    def test_coverage_loss_checks_match_type_and_dns_label_boundaries(self):
        old = {(ROOT, "example.net"), (FULL, "api.other.net"), (FULL, "notother.net")}
        candidate = {(FULL, "example.net"), (ROOT, "other.net")}
        self.assertEqual(coverage_losses(old, candidate), [(ROOT, "example.net"), (FULL, "notother.net")])
        self.assertFalse(coverage_losses(old, {(ROOT, "net")}))

    def test_habr_policy_projects_historical_input_without_excluding_habr_storage(self):
        _, _, rules = project(fixture({
            (ROOT, "habr.com"), (ROOT, "com"), (FULL, "api.habr.com"),
            (ROOT, "habrastorage.org"), (FULL, "not-habr.com"),
        }), {"habr.com"}, set())
        self.assertEqual(set(rules) - {(ROOT, n) for n in REQUIRED_ROOTS},
                         {(ROOT, "habrastorage.org"), (FULL, "not-habr.com")})

    def test_cli_follows_light_removals_and_restorations_without_approval(self):
        # Reproduce the two losses from run 45617111327, plus an arbitrary
        # suffix and exact hostname. Restore a previously removed Light name.
        removed = {(ROOT, "vtbkep.site"), (ROOT, "xn--90aifd0aza.site"),
                   (ROOT, "old-service.net"), (FULL, "api.old-service.org")}
        restored = (ROOT, "cdn-tinkoff.com")
        kept = (FULL, "api.current-service.net")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            old = tmp / "old.dat"
            source = tmp / "light.dat"
            dist = tmp / "dist"
            # Use the actual Server policy, including retained suffixes.
            from project_geosite import policy_list
            policy = Path(__file__).resolve().parents[1] / "data"
            deny = policy_list(policy / "exclude-server-suffixes.txt")
            retain = policy_list(policy / "retain-server-suffixes.txt")
            previous, _, _ = project(fixture(removed | {kept}), deny, retain)
            old.write_bytes(previous)
            source.write_bytes(fixture({restored, kept, (ROOT, "habr.com"),
                                        (ROOT, "4pda.to"), (FULL, "api.routerlogin.com")}))
            command = [sys.executable, str(Path(__file__).with_name("project_geosite.py")),
                       str(source), str(dist), "--source-sha256", digest(source.read_bytes()),
                       "--previous-server", str(old)]
            run = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertIn("Server coverage: +1 / -4", run.stdout)
            for typ, name in removed:
                self.assertIn(f"Removed coverage: {'full' if typ == FULL else 'domain'}:{name}",
                              run.stdout)
            categories, result = read_ru((dist / "geosite_RU.dat").read_bytes())
            self.assertEqual(categories, {"RU"})
            self.assertIn(restored, result)
            self.assertIn(kept, result)
            self.assertTrue(removed.isdisjoint(result))
            self.assertTrue({(ROOT, "habr.com"), (ROOT, "4pda.to"),
                             (FULL, "api.routerlogin.com")}.isdisjoint(result))
            self.assertTrue({(ROOT, name) for name in retain} <= set(result))
            self.assertEqual((dist / "geosite_RU.dat.sha256sum").read_text(),
                             digest((dist / "geosite_RU.dat").read_bytes()) + "  geosite_RU.dat\n")
            # A corrupt source checksum still fails, regardless of the relaxed delta policy.
            command[5] = "0" * 64
            bad = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("Source DAT SHA-256 does not match", bad.stderr)

    def test_deterministic_rule_order(self):
        rules = {(ROOT, "z.net"): rule(ROOT, "z.net"), (FULL, "a.net"): rule(FULL, "a.net")}
        self.assertEqual(encode(rules), encode(dict(reversed(list(rules.items())))))


if __name__ == "__main__":
    unittest.main()
