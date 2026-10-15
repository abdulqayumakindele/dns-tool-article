# How DNS Finds a Website — With a Python Demo

A beginner-friendly article on how DNS works, a simplified diagram of the lookup flow, and a small Python tool (`dnspython`) that looks up A, AAAA, CNAME, MX, NS and TXT records and traces CNAME chains. Built with Astro using the same structure as my portfolio.

> **Learning and troubleshooting tool.** It reads public DNS data by asking a DNS server ordinary questions. It does not access, modify or attack any system. Only look up domains you own or have a legitimate reason to investigate, and avoid flooding DNS servers with repeated queries.

## What the tool does
- Asks **one** DNS server (your system default, or one you choose) for the record types you request
- Prints the domain, the DNS server used, the records returned, and clear messages when there are none or a query fails
- Sorts records so repeated lookups look identical (MX by priority, addresses numerically, NS/TXT alphabetically) and adds short beginner hints under MX and SPF records
- Follows CNAME chains one hop at a time, with loop detection and a 10-hop safety limit
- Validates the domain and the `--server` address before doing anything, and reports problems in plain English instead of a traceback

## What it does *not* do
It does not perform or display the full lookup a browser triggers. The DNS server you ask does the walk through the root, top-level-domain and authoritative servers; the tool only sends the question and reports the reply. It also does not read your hosts file, use browser or operating-system caches, connect to the website, check DNSSEC, or test encrypted DNS (DoH/DoT). Its answers can therefore differ from what your browser uses. The article explains this in detail.

## Install
Requires Python 3.8 or newer and one package.

```bash
git clone https://github.com/abdulqayumakindele/dns-tool-article.git
cd dns-tool-article
pip install dnspython        # or: pip install -r tool/requirements.txt
```

## Usage
```bash
python3 tool/dns_lookup.py example.com
python3 tool/dns_lookup.py example.com -t A MX
python3 tool/dns_lookup.py example.com --server 8.8.8.8
```

| Option | Meaning | Default |
|---|---|---|
| `domain` | Domain to look up, e.g. `example.com` (no `https://` or paths) | required |
| `-t, --types` | Any of `A AAAA CNAME MX NS TXT` | all six |
| `--server` | DNS server as an IPv4 or IPv6 address, e.g. `8.8.8.8` | system default |
| `--timeout` | Seconds to wait for each answer (greater than 0, at most 60) | 5 |

### Example output
Illustrative example using documentation-only sample values (reserved `192.0.2.0/24` and `2001:db8::/32` ranges) - **not a live lookup**; real results will differ.

```text
DNS lookup for www.example.com
DNS server : 8.8.8.8 (custom)
--------------------------------------------
A      192.0.2.10
       192.0.2.20
AAAA   (none)
CNAME  edge.example.net.
MX     10 mail1.example.com.
       20 mail2.example.com.
       (lower number = tried first)
NS     ns1.example.com.
       ns2.example.com.
TXT    "hello-sample"
       "v=spf1 include:_spf.example.com ~all"
         ^ SPF: lists which servers may send email for this domain

CNAME chain: www.example.com -> edge.example.net
```

## Custom DNS servers
`--server` accepts an IPv4 or IPv6 address. Host names (`dns.google`), ports (`8.8.8.8:53`), invalid addresses and unusable addresses (`0.0.0.0`, multicast) are rejected with a clear message. Different servers can return different answers, especially right after a record changes.

## Sorted output
DNS servers rotate the order of records on purpose (round-robin), so the same lookup can list records in a different order each run. The tool sorts what it prints so two runs look identical and are easy to compare: **MX by priority** (lowest number first, which is tried first), **A/AAAA by address**, and **NS/TXT alphabetically**. Sorting only changes the display order. A TXT record starting with `v=spf1` gets a one-line note that it lists who may send email for the domain, and a single `0 .` MX record is explained as "does not accept email".

## CNAME tracing and the hop limit
A CNAME makes one name an alias of another, and that target can itself be a CNAME, forming a chain. The tool follows the chain one hop at a time. It **stops after 10 hops** because a misconfigured chain - or two names that point at each other - would otherwise repeat forever. Real chains are normally short, so reaching the limit almost always means a mistake. Loops are also detected directly (a name appearing twice), and a chain that ends at a name that does not exist is reported. The chain is traced only when `CNAME` is among the requested types (it is by default).

## When something goes wrong
| Message | Meaning |
|---|---|
| The domain does not exist (NXDOMAIN) | Name not registered / no DNS records. The tool stops. |
| No records of this type / `(none)` | The domain exists but has no record of that type - a normal result. |
| The DNS server did not answer in time | Server unreachable or slow. That record type is skipped and the others are still tried. Check your connection, try `--server`, or use `--timeout 10`. |
| The DNS server could not be used | Refused the query, or not a working DNS server. |
| Unusable response / network problem | Malformed reply or network failure, shown as a short message. |

Exit codes: `0` every lookup completed, `1` at least one lookup failed or the domain does not exist, `2` invalid command-line input.

## Limitations
- Asks one DNS server at a time; no root-to-authoritative path tracing
- Only A, AAAA, CNAME, MX, NS and TXT records
- Ignores browser/OS caches and the hosts file
- No DNSSEC checks, no DoH/DoT
- Custom servers must be IP addresses on the standard DNS port
- Not a replacement for `dig` or `nslookup`

## Tests
```bash
pip install dnspython
python3 -m unittest discover -s tests -v
```
The tests are deterministic and never contact a real DNS server: they use a fake resolver with scripted answers and errors. They cover argument validation, DNS-server validation, all six record types, CNAME multi-hop/loop/hop-limit/dangling cases, and each DNS error path. (If `dnspython` is not installed, the tests fall back to a small built-in stub and print a note; install `dnspython` for the full check.)

## Project website (Astro)
```bash
npm install
npm run dev      # local site
npm run build    # production build in dist/
```
Article text and all site content live in `src/data/content.js`. The tool code is shown on the Tool page straight from `tool/dns_lookup.py`.

## Structure
```text
tool/dns_lookup.py        the DNS tool
tool/requirements.txt     dnspython
tests/                    unit tests
src/data/content.js       article + all site content
src/pages/                index, article, tool, resources
src/components/           Header, Footer
src/layouts/Layout.astro  shared layout
src/styles/global.css     theme
```

Author: Abdul Qayum Akindele
