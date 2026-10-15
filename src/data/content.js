// ─────────────────────────────────────────────
// SITE — edit here, pages update automatically
// ─────────────────────────────────────────────
export const site = {
  name: 'How DNS Finds a Website — With a Python Demo',
  brand: 'HOW DNS FINDS A WEBSITE',
  tagline: 'A beginner-friendly article plus a Python tool that turns the concept into something you can run.',
  description: 'A beginner guide to how DNS works, with a diagram and a Python dnspython tool that looks up A, AAAA, CNAME, MX, NS and TXT records. By Abdul Qayum Akindele.',
  url: 'https://dns-tool-article.netlify.app',
  repo: 'https://github.com/abdulqayumakindele/dns-tool-article',
  links: [
    ['GitHub Repo', 'https://github.com/abdulqayumakindele/dns-tool-article'],
    ['Portfolio',   'https://abdulqayum.netlify.app'],
    ['LinkedIn',    'https://www.linkedin.com/in/abdul-qayum-akindele-bb33573a3'],
  ],
};

export const stack = ['Python 3', 'dnspython', 'Astro'];

// ─────────────────────────────────────────────
// ARTICLE — add or edit sections here
// ─────────────────────────────────────────────
export const article = {
  "title": "How DNS Finds a Website — With a Python Demo",
  "author": "Abdul Qayum Akindele",
  "intro": "Every time you type a website address, your device has to answer one question before anything loads: which IP address belongs to this name? DNS, the Domain Name System, answers it. This article explains how, and what a small Python tool can and cannot show you about the process.",
  "sections": [
    {
      "heading": "What DNS is",
      "paragraphs": [
        "Computers find each other using IP addresses such as 192.0.2.10, but people remember names like example.com. DNS is a distributed system that translates names into the records computers need, most often an IP address. No single server holds everything: the information is spread across many servers around the world, each responsible for its own part."
      ]
    },
    {
      "heading": "What a DNS resolver does",
      "paragraphs": [
        "Your device does not usually search the whole system itself. A small component on your device, the stub resolver, passes the question to a recursive resolver, typically run by your internet provider or a public service. The recursive resolver does the searching on your behalf.",
        "If the recursive resolver does not already have the answer cached, it works down the hierarchy: it asks a root server which servers handle the top-level domain (such as .com), asks those which servers are authoritative for the domain, and finally asks the authoritative nameserver, which holds the real records. The answer is returned to your device and cached for a period set by the record's TTL (time to live), so repeat lookups are fast."
      ]
    },
    {
      "heading": "Common DNS record types",
      "paragraphs": [
        "DNS stores more than addresses. An A record maps a name to an IPv4 address and an AAAA record maps it to an IPv6 address. A CNAME record says a name is an alias of another name. An MX record lists the mail servers for the domain, each with a priority number (lower numbers are preferred). An NS record lists the domain's authoritative nameservers. A TXT record holds free-form text, often used to prove domain ownership or to publish email-security policies."
      ]
    },
    {
      "heading": "CNAME chains",
      "paragraphs": [
        "A CNAME points one name at another name, and that name can itself be a CNAME, forming a chain: www.example.com might point to a hosting provider's name, which points to another name, which finally has an A record. Resolvers follow the chain for you until they reach an address.",
        "Chains can be misconfigured. Two names can point at each other (a loop), or a chain can end at a name that does not exist. Any tool that follows chains therefore needs a maximum hop limit, otherwise a loop would run forever. This tool stops after 10 hops and also detects loops directly. Real-world chains are normally short, so hitting the limit almost always means a mistake."
      ]
    },
    {
      "heading": "What the Python tool actually does",
      "paragraphs": [
        "The tool uses the dnspython library to send DNS queries to one DNS server and print the answers. For each record type you ask for, it sends a separate query and shows the records returned, or a clear message if there are none or the query failed. The records are sorted before printing (MX by priority, addresses numerically, the rest alphabetically), because DNS servers rotate record order on purpose and unsorted output would change from run to run. To trace a CNAME chain, it asks for the CNAME record of the domain, then of the name it points to, and so on, until the chain ends, loops, or reaches the hop limit.",
        "The DNS server it asks is your system's default resolver, or the one you choose with --server. That server does the walk through the root, top-level-domain, and authoritative servers; the tool itself only asks the question and reports the reply. It does not, for example, list every server involved in the lookup."
      ]
    },
    {
      "heading": "Python query vs. what a browser does",
      "paragraphs": [
        "When a browser opens a website, far more happens than one DNS query. The browser checks its own cache, and may use its own secure-DNS settings. The operating system checks its cache and its hosts file before the stub resolver contacts a recursive resolver. Once an address is known, the browser still has to open a network connection, set up encryption (TLS), and send the web request.",
        "The Python tool covers only the DNS-question part, and only against the server you point it at. It does not read the hosts file, use browser or operating-system caches, or connect to the website. Because of that, its answers can differ from what your browser uses, for example when a site returns different addresses depending on location or when a server has cached an older answer."
      ]
    },
    {
      "heading": "Using a custom DNS server",
      "paragraphs": [
        "By default the tool asks the DNS server your system is configured to use. With --server you can ask a different one, such as 8.8.8.8 or 1.1.1.1, to compare answers. The value must be an IPv4 or IPv6 address, not a host name, and the standard DNS port is used. If the server is unreachable or does not respond, the tool tells you instead of crashing. Different servers can legitimately return different answers, especially right after a record has been changed."
      ]
    },
    {
      "heading": "Limitations",
      "paragraphs": [
        "The tool looks up six record types (A, AAAA, CNAME, MX, NS, TXT) using one server at a time. It does not trace the full root-to-authoritative path, check DNSSEC signatures, test encrypted DNS (DNS over HTTPS or TLS), monitor changes over time, or replace mature tools such as dig or nslookup. Its results describe what the chosen server answered at that moment, and cached answers may be slightly out of date."
      ]
    },
    {
      "heading": "Why it matters for security",
      "paragraphs": [
        "DNS is both a target and a source of information. Attackers can abuse it, for example with lookalike domains or forged responses, while defenders read DNS records to check email-authentication settings and to investigate suspicious domains. Understanding how a lookup works is a solid foundation for both. Use tools like this one only to learn and to check domains you are allowed to investigate."
      ]
    }
  ]
};

export const toolUsage = [
  'python3 tool/dns_lookup.py example.com',
  'python3 tool/dns_lookup.py example.com -t A MX',
  'python3 tool/dns_lookup.py example.com --server 8.8.8.8',
];

export const recordTypes = [
  ['A', 'IPv4 address of the domain'], ['AAAA', 'IPv6 address of the domain'],
  ['CNAME', 'Alias pointing to another name'], ['MX', 'Mail servers for the domain'],
  ['NS', 'Authoritative nameservers'], ['TXT', 'Free-form text (verification, email policies)'],
];

export const resources = [
  { title: 'My earlier DNS article on Dev.to', url: 'https://dev.to/off_limit001/dns-explained-how-your-device-finds-a-website-on-the-internet-4p0a', description: 'The original beginner-friendly explanation this project expands on.' },
  { title: 'dnspython documentation', url: 'https://dnspython.readthedocs.io', description: 'Official docs for the library used in the tool.' },
];

// ─────────────────────────────────────────────
// TOOL PAGE CONTENT
// ─────────────────────────────────────────────
export const install = [
  'Install Python 3.8 or newer (check with: python3 --version).',
  'Download or clone the repository: git clone ' + site.repo + '.git',
  'Install the one dependency: pip install dnspython   (or: pip install -r tool/requirements.txt)',
  'Run it: python3 tool/dns_lookup.py example.com',
];

export const toolOptions = [
  ['domain',         'The domain to look up, e.g. example.com (no https:// or paths)', 'required'],
  ['-t, --types',    'Record types to look up: A AAAA CNAME MX NS TXT',                'all six'],
  ['--server',       'DNS server to ask, as an IPv4 or IPv6 address, e.g. 8.8.8.8',   'system default'],
  ['--timeout',      'Seconds to wait for each answer (greater than 0, at most 60)',   '5'],
];

export const cnameNotes = [
  'The tool follows a CNAME chain one hop at a time, asking for the CNAME record of each name it reaches.',
  'It stops after 10 hops. This maximum hop limit is a safety measure: a misconfigured chain, or two names pointing at each other, would otherwise repeat forever. Real chains are normally short, so reaching the limit almost always signals a mistake.',
  'It also detects loops directly: if a name appears twice in the chain, it stops and warns you.',
  'If a chain ends at a name that does not exist, or a DNS error happens partway, the tool shows the chain so far and explains what went wrong.',
  'The chain is only traced when CNAME is among the record types requested (it is by default).',
];

export const errorNotes = [
  ['Domain does not exist (NXDOMAIN)', 'The name is not registered or has no DNS records at all. The tool stops instead of asking for more types.'],
  ['No records of this type', 'The domain exists but has no record of that type — for example no AAAA record. This is a normal result, shown as (none).'],
  ['Server did not answer in time', 'The DNS server is unreachable or too slow. That record type is skipped and the others are still tried. Check your connection, try --server, or allow more time with --timeout 10.'],
  ['Server could not be used', 'The server refused the query or is not a working DNS server.'],
  ['Unusable response / network problem', 'The response was malformed, or the network failed while contacting the server. Shown as a short message, not a traceback.'],
];

export const toolLimitations = [
  'Asks one DNS server at a time — it does not trace the full path from the root servers to the authoritative server',
  'Looks up only A, AAAA, CNAME, MX, NS and TXT records',
  'Does not use your browser or operating-system cache, or your hosts file, so results can differ from what your browser uses',
  'Does not check DNSSEC or test encrypted DNS (DNS over HTTPS/TLS)',
  'Custom servers must be given as IP addresses; a non-standard port cannot be set',
  'Shows what the chosen server answered at that moment; cached answers may be slightly out of date',
];

export const responsibleUse = [
  'This is a learning and troubleshooting tool. DNS lookups are ordinary queries that anyone can make, and the tool only reads public DNS data.',
  'It does not access, modify, or attack any system.',
  'Only investigate domains you own or have a legitimate reason to look up, and respect the terms of the DNS server you query. Do not flood servers with repeated queries.',
];

export const exampleOutput = `DNS lookup for www.example.com
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

CNAME chain: www.example.com -> edge.example.net`;
export const exampleNote = 'Illustrative example using documentation-only sample values for www.example.com (addresses from the reserved 192.0.2.0/24 and 2001:db8::/32 ranges). It is not a live lookup — real results will differ.';

// ─────────────────────────────────────────────
// SORTED OUTPUT + FIELD NOTE
// ─────────────────────────────────────────────
export const sortNotes = [
  'DNS servers deliberately rotate the order of records (called round-robin) to spread traffic, so the same lookup can list records in a different order each time.',
  'The tool sorts what it prints so two runs of the same lookup look identical and are easy to compare: MX records by priority number (lowest first), A and AAAA records by address, and NS and TXT records alphabetically.',
  'For MX records, a lower number means that mail server is tried first, so the primary mail server always appears at the top. A single record "0 ." (a "null MX") means the domain does not accept email.',
  'A TXT record that starts with v=spf1 is an SPF policy: it lists which servers are allowed to send email for the domain. The tool adds a one-line note under it.',
  'Sorting only changes the display order. The records themselves are exactly what the server returned.',
];

// Edit the wording to match what really happened when you cross-checked with dig.
export const fieldNote = {
  title: 'A bug found through real use',
  text: 'Repeating the same lookup showed the same records in a different order each time, which made results hard to compare, including against dig. DNS servers rotate record order on purpose, so the tool now sorts its output.',
};
