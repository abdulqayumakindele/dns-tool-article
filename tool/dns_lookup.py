#!/usr/bin/env python3
"""
DNS Lookup Tool
---------------
Looks up DNS records (A, AAAA, CNAME, MX, NS, TXT) for a domain and follows
CNAME chains, using the dnspython library.

The tool asks ONE DNS server (your system's default resolver, or the one you
choose with --server) and prints what it answers. It does not perform the
full lookup process a browser uses (see the project article for the
difference).

Install:  pip install dnspython
Usage:    python3 tool/dns_lookup.py example.com
          python3 tool/dns_lookup.py example.com -t A MX --server 8.8.8.8

For learning and troubleshooting. DNS lookups are ordinary public queries,
but only query domains you are allowed to investigate.
"""

import argparse
import ipaddress
import math
import sys
from collections import namedtuple

import dns.exception
import dns.name
import dns.resolver

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "TXT"]
MAX_CNAME_HOPS = 10     # safety limit: stops endless or absurdly long chains
QUERY_TIMEOUT = 5       # default seconds to wait for a DNS server before giving up
MAX_TIMEOUT = 60

Result = namedtuple("Result", "status records message")

# Statuses that mean "no point asking for more record types".
# (A timeout is NOT here: one slow answer should not discard the others.)
FATAL_STATUSES = {"nxdomain", "no_nameservers"}

STATUS_MESSAGES = {
    "nxdomain": "The domain does not exist (NXDOMAIN).",
    "no_answer": "No records of this type.",
    "timeout": "The DNS server did not answer in time. Check your internet "
               "connection, try a different server with --server, or allow "
               "more time with --timeout 10.",
    "no_nameservers": "The DNS server could not be used or refused the query. "
                      "Check that the address is a working DNS server.",
}


class InputError(ValueError):
    """Bad user input. The message is written for beginners."""


# ── Validation ────────────────────────────────────────────────────────────

def validate_domain(text):
    """Return a cleaned domain name, or explain what is wrong with it."""
    text = (text or "").strip()
    if not text:
        raise InputError("Please give a domain name, for example: example.com")
    if any(ch.isspace() for ch in text) or "/" in text or "@" in text or "://" in text:
        raise InputError(
            f"'{text}' does not look like a plain domain name. Give just the "
            "domain, such as example.com (no https://, paths, or spaces)."
        )
    try:
        dns.name.from_text(text)
    except (dns.exception.DNSException, UnicodeError):
        raise InputError(
            f"'{text}' is not a valid domain name. Check for empty parts "
            "(like 'a..com') or parts longer than 63 characters."
        ) from None
    return text.rstrip(".") or text


def validate_server(text):
    """Return a DNS server IP address (IPv4 or IPv6) as text, or explain the problem."""
    text = (text or "").strip()
    if not text:
        raise InputError("--server needs an IP address, such as 8.8.8.8 or 2001:4860:4860::8888.")
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        raise InputError(
            f"'{text}' is not a valid IP address. Give the DNS server as an IPv4 "
            "or IPv6 address such as 1.1.1.1 (host names and ports are not accepted)."
        ) from None
    if address.is_unspecified or address.is_multicast:
        raise InputError(f"'{text}' cannot be used as a DNS server address.")
    return str(address)


def domain_arg(text):
    try:
        return validate_domain(text)
    except InputError as err:
        raise argparse.ArgumentTypeError(str(err)) from None


def timeout_arg(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' is not a number. Example: --timeout 10"
        ) from None
    if math.isnan(value) or math.isinf(value) or not 0 < value <= MAX_TIMEOUT:
        raise argparse.ArgumentTypeError(
            f"Timeout must be greater than 0 and at most {MAX_TIMEOUT} seconds."
        )
    return value


def server_arg(text):
    try:
        return validate_server(text)
    except InputError as err:
        raise argparse.ArgumentTypeError(str(err)) from None


# ── DNS queries ───────────────────────────────────────────────────────────

def make_resolver(server=None, timeout=QUERY_TIMEOUT):
    """Build a resolver: the system default, or one custom server."""
    try:
        resolver = dns.resolver.Resolver(configure=server is None)
    except dns.resolver.NoResolverConfiguration:
        raise InputError(
            "No DNS server is configured on this system. "
            "Choose one with --server, for example --server 8.8.8.8."
        ) from None
    if server:
        resolver.nameservers = [server]
    resolver.lifetime = timeout
    return resolver


def describe_server(resolver, custom):
    servers = ", ".join(str(s) for s in resolver.nameservers)
    return f"{servers} ({'custom' if custom else 'system default'})"


def _mx_key(text):
    """MX records look like '10 mail.example.com.': sort by number, then name."""
    parts = text.split(None, 1)
    try:
        priority = int(parts[0])
    except (ValueError, IndexError):
        return (1, 0, text.lower(), text)          # malformed: put last, never crash
    name = parts[1] if len(parts) > 1 else ""
    return (0, priority, name.lower(), text)


def _ip_key(text):
    """Sort IP addresses by their numeric value (so 10.0.0.2 comes before 10.0.0.10)."""
    try:
        return (0, int(ipaddress.ip_address(text)), text)
    except ValueError:
        return (1, 0, text)


def sort_records(rtype, records):
    """
    Return records in a stable order. DNS servers rotate the order of records
    on purpose, so without sorting, two runs of the same lookup can look
    different. MX is sorted by priority (lowest first, the one tried first),
    A/AAAA by address, and everything else alphabetically.
    """
    if rtype == "MX":
        return sorted(records, key=_mx_key)
    if rtype in ("A", "AAAA"):
        return sorted(records, key=_ip_key)
    return sorted(records, key=lambda text: (text.lower(), text))


def is_spf(text):
    """True for a TXT record that starts with v=spf1 (an SPF email policy)."""
    return text.strip().strip('"').lower().startswith("v=spf1")


def query(resolver, name, rtype):
    """Ask for one record type. Never raises for expected DNS problems."""
    try:
        answers = resolver.resolve(name, rtype)
    except dns.resolver.NXDOMAIN:
        return Result("nxdomain", [], STATUS_MESSAGES["nxdomain"])
    except dns.resolver.NoAnswer:
        return Result("no_answer", [], STATUS_MESSAGES["no_answer"])
    except dns.resolver.NoNameservers:
        return Result("no_nameservers", [], STATUS_MESSAGES["no_nameservers"])
    except dns.exception.Timeout:
        return Result("timeout", [], STATUS_MESSAGES["timeout"])
    except dns.exception.DNSException as err:      # e.g. malformed/invalid response
        detail = str(err).strip() or type(err).__name__
        return Result("error", [], f"The DNS server sent a response that could not be used ({detail}).")
    except OSError as err:                         # network unreachable, etc.
        return Result("error", [], f"Network problem while contacting the DNS server ({err}).")
    return Result("ok", sort_records(rtype, [rr.to_text() for rr in answers]), "")


def trace_cname(resolver, name, max_hops=MAX_CNAME_HOPS):
    """
    Follow a CNAME chain one hop at a time.
    Returns (chain, outcome, message) where outcome is one of:
    'end' (chain finished normally), 'loop', 'max_hops',
    or a DNS problem status such as 'nxdomain' or 'timeout'.
    """
    chain = [name]
    seen = {name.lower()}
    while True:
        result = query(resolver, chain[-1], "CNAME")
        if result.status == "no_answer":
            return chain, "end", ""
        if result.status != "ok":
            return chain, result.status, result.message
        target = result.records[0].rstrip(".")
        if target.lower() in seen:
            chain.append(target)
            return chain, "loop", ""
        if len(chain) - 1 >= max_hops:
            return chain, "max_hops", ""
        chain.append(target)
        seen.add(target.lower())


# ── Command-line interface ────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(description="Simple DNS record lookup tool (for learning and troubleshooting).")
    parser.add_argument("domain", type=domain_arg, help="domain name, e.g. example.com")
    parser.add_argument("-t", "--types", nargs="+", default=RECORD_TYPES,
                        type=str.upper, choices=RECORD_TYPES, metavar="TYPE",
                        help=f"record types to look up (choose from {', '.join(RECORD_TYPES)}; default: all)")
    parser.add_argument("--server", type=server_arg,
                        help="DNS server IP to ask instead of the system default, e.g. 8.8.8.8")
    parser.add_argument("--timeout", type=timeout_arg, default=QUERY_TIMEOUT,
                        help=f"seconds to wait for each answer (default: {QUERY_TIMEOUT}, max: {MAX_TIMEOUT})")
    return parser


def print_records(rtype, result):
    if result.status == "ok":
        lines = []
        for record in result.records:
            lines.append(record)
            if rtype == "TXT" and is_spf(record):
                lines.append("  ^ SPF: lists which servers may send email for this domain")
        if rtype == "MX":
            if result.records == ["0 ."]:
                lines.append("(0 . means this domain does not accept email)")
            else:
                lines.append("(lower number = tried first)")
        print(f"{rtype:<6} " + "\n       ".join(lines))
    elif result.status == "no_answer":
        print(f"{rtype:<6} (none)")
    else:
        print(f"{rtype:<6} [!] {result.message}")


def print_cname_trace(chain, outcome, message):
    if len(chain) > 1:
        print("\nCNAME chain: " + " -> ".join(chain))
    else:
        print("\nCNAME chain: none (this name is not an alias)")
    if outcome == "loop":
        print(f"[!] CNAME loop detected: '{chain[-1]}' was already in the chain.")
    elif outcome == "max_hops":
        print(f"[!] Stopped after {MAX_CNAME_HOPS} hops (safety limit); the chain may continue.")
    elif outcome == "nxdomain" and len(chain) > 1:
        print(f"[!] The chain ends at '{chain[-1]}', which does not exist (NXDOMAIN).")
    elif outcome not in ("end", "nxdomain"):
        print(f"[!] Could not finish tracing: {message}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    types = list(dict.fromkeys(args.types))          # remove duplicates, keep order

    try:
        resolver = make_resolver(args.server, args.timeout)
    except InputError as err:
        print(f"[!] {err}", file=sys.stderr)
        return 1

    print(f"DNS lookup for {args.domain}")
    print(f"DNS server : {describe_server(resolver, bool(args.server))}")
    print("-" * 44)

    succeeded = failed = 0
    for rtype in types:
        result = query(resolver, args.domain, rtype)
        if result.status in FATAL_STATUSES:
            print(f"[!] {result.message}")
            return 1
        if result.status in ("ok", "no_answer"):
            succeeded += 1
        else:
            failed += 1
        print_records(rtype, result)

    if succeeded == 0:
        print("\n[!] No lookup could be completed, so the CNAME chain was not traced.")
        return 1
    if "CNAME" in types:
        print_cname_trace(*trace_cname(resolver, args.domain))
    if failed:
        print(f"\n[!] {failed} of {len(types)} lookups failed (see messages above). "
              "Results shown may be incomplete.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit("\n[!] Cancelled.")
