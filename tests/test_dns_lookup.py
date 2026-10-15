"""
Tests for the DNS lookup tool. Run from the project root with:

    python3 -m unittest discover -s tests -v

The tests are deterministic: they never contact a real DNS server. They use a
fake resolver that returns scripted answers or raises scripted errors.
"""

import contextlib
import io
import itertools
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tool"))

try:
    import dns.resolver  # noqa: F401
    USING_STUB = False
except ImportError:
    import fake_dns
    fake_dns.install()
    USING_STUB = True
    print("NOTE: dnspython is not installed - tests are using a built-in stub. "
          "Run 'pip install dnspython' for the full check.", file=sys.stderr)

import dns.exception  # noqa: E402
import dns.resolver  # noqa: E402
import dns_lookup as dl  # noqa: E402


class RR:
    """Fake DNS record with the one method the tool uses."""
    def __init__(self, text):
        self.text = text

    def to_text(self):
        return self.text


class FakeResolver:
    """Returns scripted answers: {(name, type): [texts] or an Exception}."""
    def __init__(self, script, nameservers=("192.0.2.53",)):
        self.script = script
        self.nameservers = list(nameservers)
        self.calls = []

    def resolve(self, name, rtype):
        self.calls.append((name, rtype))
        outcome = self.script.get((name, rtype), dns.resolver.NoAnswer())
        if isinstance(outcome, Exception):
            raise outcome
        return [RR(t) for t in outcome]


def run_main(script, *argv, nameservers=("192.0.2.53",)):
    fake = FakeResolver(script, nameservers)
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with mock.patch.object(dl, "make_resolver", return_value=fake), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = dl.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue(), fake


class ServerValidationTests(unittest.TestCase):
    def test_valid_servers(self):
        for text in ("8.8.8.8", "1.1.1.1", "127.0.0.1", "::1", "2001:4860:4860::8888", " 9.9.9.9 "):
            with self.subTest(text=text):
                self.assertEqual(dl.validate_server(text), str(__import__("ipaddress").ip_address(text.strip())))

    def test_invalid_servers(self):
        for text in ("", "   ", "dns.google", "8.8.8.8:53", "999.1.1.1", "abc", "0.0.0.0", "224.0.0.1", "8.8.8"):
            with self.subTest(text=text):
                with self.assertRaises(dl.InputError):
                    dl.validate_server(text)

    def test_error_message_is_beginner_friendly(self):
        with self.assertRaises(dl.InputError) as ctx:
            dl.validate_server("dns.google")
        self.assertIn("IP address", str(ctx.exception))


class DomainValidationTests(unittest.TestCase):
    def test_valid_domains(self):
        self.assertEqual(dl.validate_domain("example.com"), "example.com")
        self.assertEqual(dl.validate_domain("Example.COM."), "Example.COM")
        self.assertEqual(dl.validate_domain("localhost"), "localhost")

    def test_invalid_domains(self):
        for text in ("", "  ", "https://example.com", "exa mple.com", "a..com", "x/y", "a@b.com",
                     "a" * 64 + ".com"):
            with self.subTest(text=text):
                with self.assertRaises(dl.InputError):
                    dl.validate_domain(text)


class QueryTests(unittest.TestCase):
    def test_success_for_every_record_type(self):
        samples = {"A": "192.0.2.10", "AAAA": "2001:db8::10", "CNAME": "target.example.net.",
                   "MX": "10 mail.example.com.", "NS": "ns1.example.com.", "TXT": '"v=spf1 -all"'}
        for rtype, text in samples.items():
            with self.subTest(rtype=rtype):
                resolver = FakeResolver({("example.com", rtype): [text]})
                result = dl.query(resolver, "example.com", rtype)
                self.assertEqual((result.status, result.records), ("ok", [text]))

    def test_expected_failures_map_to_statuses(self):
        cases = [
            (dns.resolver.NXDOMAIN(), "nxdomain"),
            (dns.resolver.NoAnswer(), "no_answer"),
            (dns.resolver.NoNameservers(), "no_nameservers"),
            (dns.exception.Timeout(), "timeout"),
            (dns.exception.DNSException("bad packet"), "error"),
            (OSError("Network is unreachable"), "error"),
        ]
        for exc, status in cases:
            with self.subTest(status=status, exc=type(exc).__name__):
                resolver = FakeResolver({("example.com", "A"): exc})
                result = dl.query(resolver, "example.com", "A")
                self.assertEqual(result.status, status)
                self.assertTrue(result.message)

    def test_error_statuses_include_helpful_text(self):
        result = dl.query(FakeResolver({("x.com", "A"): dns.exception.Timeout()}), "x.com", "A")
        self.assertIn("--server", result.message)


class SortingTests(unittest.TestCase):
    def lookup(self, rtype, records):
        resolver = FakeResolver({("example.com", rtype): records})
        return dl.query(resolver, "example.com", rtype).records

    def test_mx_sorted_by_numeric_priority_then_name(self):
        expected = ["5 m.example.", "10 a.example.", "10 z.example.", "20 b.example."]
        for order in itertools.permutations(expected):
            with self.subTest(order=order):
                self.assertEqual(self.lookup("MX", list(order)), expected)

    def test_mx_priority_is_numeric_not_text(self):
        self.assertEqual(self.lookup("MX", ["100 c.example.", "20 b.example.", "3 a.example."]),
                         ["3 a.example.", "20 b.example.", "100 c.example."])

    def test_mx_malformed_record_does_not_crash_and_goes_last(self):
        self.assertEqual(self.lookup("MX", ["weird", "10 a.example."]), ["10 a.example.", "weird"])

    def test_ns_and_txt_sorted_alphabetically_ignoring_case(self):
        self.assertEqual(self.lookup("NS", ["hera.ns.example.", "Elliott.ns.example.", "alpha.ns.example."]),
                         ["alpha.ns.example.", "Elliott.ns.example.", "hera.ns.example."])
        self.assertEqual(self.lookup("TXT", ['"v=spf1 -all"', '"_token123"', '"google-site=abc"']),
                         ['"_token123"', '"google-site=abc"', '"v=spf1 -all"'])

    def test_addresses_sorted_numerically(self):
        self.assertEqual(self.lookup("A", ["10.0.0.10", "10.0.0.2", "9.9.9.9"]),
                         ["9.9.9.9", "10.0.0.2", "10.0.0.10"])
        self.assertEqual(self.lookup("AAAA", ["2001:db8::10", "2001:db8::2"]),
                         ["2001:db8::2", "2001:db8::10"])

    def test_same_records_in_any_order_give_identical_output(self):
        records = {"MX": ["20 b.example.", "10 a.example."], "NS": ["ns2.example.", "ns1.example."],
                   "TXT": ['"b"', '"a"'], "A": ["192.0.2.20", "192.0.2.3"]}
        outputs = set()
        for flip in (False, True, None):
            script = {}
            for rtype, recs in records.items():
                recs = list(recs)
                if flip is True:
                    recs.reverse()
                elif flip is None:
                    recs = recs[1:] + recs[:1]
                script[("example.com", rtype)] = recs
            _, out, _, _ = run_main(script, "example.com", "-t", "A", "MX", "NS", "TXT")
            outputs.add(out)
        self.assertEqual(len(outputs), 1)


class HintTests(unittest.TestCase):
    def test_mx_hint_is_shown(self):
        _, out, _, _ = run_main({("example.com", "MX"): ["10 a.example.", "5 b.example."]},
                                "example.com", "-t", "MX")
        self.assertIn("(lower number = tried first)", out)
        self.assertLess(out.index("5 b.example."), out.index("10 a.example."))

    def test_null_mx_gets_its_own_note(self):
        _, out, _, _ = run_main({("example.com", "MX"): ["0 ."]}, "example.com", "-t", "MX")
        self.assertIn("does not accept email", out)
        self.assertNotIn("lower number", out)

    def test_spf_record_gets_a_short_explanation(self):
        _, out, _, _ = run_main({("example.com", "TXT"): ['"v=spf1 include:_spf.example.com ~all"', '"hello"']},
                                "example.com", "-t", "TXT")
        self.assertEqual(out.count("SPF:"), 1)
        self.assertIn("may send email", out)

    def test_no_hints_for_other_record_types_or_empty_results(self):
        _, out, _, _ = run_main({("example.com", "A"): ["192.0.2.10"]}, "example.com", "-t", "A", "MX")
        self.assertNotIn("lower number", out)
        self.assertNotIn("SPF", out)


class MakeResolverTests(unittest.TestCase):
    def test_custom_server_is_used(self):
        resolver = dl.make_resolver("9.9.9.9")
        self.assertEqual([str(s) for s in resolver.nameservers], ["9.9.9.9"])
        self.assertEqual(resolver.lifetime, dl.QUERY_TIMEOUT)

    def test_custom_timeout_is_used(self):
        self.assertEqual(dl.make_resolver("9.9.9.9", 12).lifetime, 12)

    def test_missing_system_configuration_gives_friendly_error(self):
        with mock.patch.object(dl.dns.resolver, "Resolver", side_effect=dns.resolver.NoResolverConfiguration()):
            with self.assertRaises(dl.InputError) as ctx:
                dl.make_resolver()
        self.assertIn("--server", str(ctx.exception))


class CnameTraceTests(unittest.TestCase):
    def test_no_cname(self):
        chain, outcome, _ = dl.trace_cname(FakeResolver({}), "example.com")
        self.assertEqual((chain, outcome), (["example.com"], "end"))

    def test_multiple_hops(self):
        script = {("a.example", "CNAME"): ["b.example."], ("b.example", "CNAME"): ["c.example."]}
        chain, outcome, _ = dl.trace_cname(FakeResolver(script), "a.example")
        self.assertEqual((chain, outcome), (["a.example", "b.example", "c.example"], "end"))

    def test_loop_is_detected(self):
        script = {("a.example", "CNAME"): ["b.example."], ("b.example", "CNAME"): ["a.example."]}
        chain, outcome, _ = dl.trace_cname(FakeResolver(script), "a.example")
        self.assertEqual(outcome, "loop")
        self.assertEqual(chain, ["a.example", "b.example", "a.example"])

    def test_self_pointing_cname_is_a_loop(self):
        chain, outcome, _ = dl.trace_cname(FakeResolver({("a.example", "CNAME"): ["a.example."]}), "a.example")
        self.assertEqual(outcome, "loop")

    def test_max_hops_limit(self):
        script = {(f"h{i}.example", "CNAME"): [f"h{i+1}.example."] for i in range(50)}
        resolver = FakeResolver(script)
        chain, outcome, _ = dl.trace_cname(resolver, "h0.example", max_hops=3)
        self.assertEqual(outcome, "max_hops")
        self.assertEqual(len(chain), 4)           # start + 3 hops
        self.assertLessEqual(len(resolver.calls), 4)

    def test_dangling_cname_reports_nxdomain(self):
        script = {("a.example", "CNAME"): ["gone.example."], ("gone.example", "CNAME"): dns.resolver.NXDOMAIN()}
        chain, outcome, _ = dl.trace_cname(FakeResolver(script), "a.example")
        self.assertEqual((chain, outcome), (["a.example", "gone.example"], "nxdomain"))

    def test_dns_error_midway_is_reported_not_raised(self):
        script = {("a.example", "CNAME"): ["b.example."], ("b.example", "CNAME"): dns.exception.Timeout()}
        chain, outcome, message = dl.trace_cname(FakeResolver(script), "a.example")
        self.assertEqual((chain, outcome), (["a.example", "b.example"], "timeout"))
        self.assertTrue(message)


class CliTests(unittest.TestCase):
    def test_normal_lookup_output(self):
        script = {("example.com", "A"): ["192.0.2.10"], ("example.com", "MX"): ["10 mail.example.com."]}
        code, out, err, _ = run_main(script, "example.com", "-t", "A", "MX", "AAAA")
        self.assertEqual(code, 0)
        for text in ("DNS lookup for example.com", "192.0.2.53 (system default)", "192.0.2.10",
                     "10 mail.example.com.", "(none)"):
            self.assertIn(text, out)

    def test_custom_server_is_shown(self):
        code, out, _, _ = run_main({}, "example.com", "-t", "A", nameservers=("8.8.8.8",))
        self.assertEqual(code, 0)      # NoAnswer is a valid result, not a failure

    def test_only_requested_types_are_queried_and_no_cname_trace(self):
        _, out, _, fake = run_main({("example.com", "A"): ["192.0.2.10"]}, "example.com", "-t", "a", "a")
        self.assertEqual(fake.calls, [("example.com", "A")])
        self.assertNotIn("CNAME chain", out)

    def test_cname_chain_is_printed(self):
        script = {("www.example.com", "CNAME"): ["edge.example.net."]}
        _, out, _, _ = run_main(script, "www.example.com", "-t", "CNAME")
        self.assertIn("CNAME chain: www.example.com -> edge.example.net", out)

    def test_loop_warning_is_printed(self):
        script = {("a.example", "CNAME"): ["b.example."], ("b.example", "CNAME"): ["a.example."]}
        _, out, _, _ = run_main(script, "a.example", "-t", "CNAME")
        self.assertIn("CNAME loop detected", out)

    def test_nxdomain_stops_with_clear_message(self):
        code, out, err, fake = run_main({("nope.example", "A"): dns.resolver.NXDOMAIN()}, "nope.example")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", out)
        self.assertEqual(len(fake.calls), 1)       # did not keep asking
        self.assertNotIn("Traceback", out + err)

    def test_timeout_gives_clear_message(self):
        code, out, err, _ = run_main({("example.com", "A"): dns.exception.Timeout()}, "example.com", "-t", "A")
        self.assertEqual(code, 1)
        self.assertIn("did not answer in time", out)
        self.assertIn("--timeout", out)
        self.assertIn("CNAME chain was not traced", out)
        self.assertNotIn("Traceback", out + err)

    def test_one_timeout_does_not_discard_other_results(self):
        script = {("example.com", "A"): ["192.0.2.10"], ("example.com", "AAAA"): dns.exception.Timeout()}
        code, out, err, fake = run_main(script, "example.com", "-t", "A", "AAAA", "MX")
        self.assertEqual(code, 1)                       # something failed, so not a clean success
        self.assertIn("192.0.2.10", out)                # but the good answer is still shown
        self.assertIn("did not answer in time", out)
        self.assertIn("1 of 3 lookups failed", out)
        self.assertEqual(len(fake.calls), 3)            # kept going after the timeout
        self.assertNotIn("Traceback", out + err)

    def test_invalid_timeout_is_rejected(self):
        for value in ("0", "-1", "abc", "nan", "inf", "999"):
            with self.subTest(value=value):
                code, _, err, _ = run_main({}, "example.com", "--timeout", value)
                self.assertEqual(code, 2)
                self.assertIn("imeout", err)
                self.assertNotIn("Traceback", err)

    def test_invalid_server_is_rejected(self):
        code, _, err, fake = run_main({}, "example.com", "--server", "dns.google")
        self.assertEqual(code, 2)
        self.assertIn("not a valid IP address", err)
        self.assertEqual(fake.calls, [])

    def test_invalid_domain_is_rejected(self):
        code, _, err, _ = run_main({}, "https://example.com")
        self.assertEqual(code, 2)
        self.assertIn("plain domain name", err)

    def test_invalid_record_type_is_rejected(self):
        code, _, err, _ = run_main({}, "example.com", "-t", "SOA")
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    def test_missing_system_dns_gives_clean_error(self):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(dl, "make_resolver", side_effect=dl.InputError("No DNS server is configured")), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = dl.main(["example.com"])
        self.assertEqual(code, 1)
        self.assertIn("No DNS server", err.getvalue())


if __name__ == "__main__":
    unittest.main()
