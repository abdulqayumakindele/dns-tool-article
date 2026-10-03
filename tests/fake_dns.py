"""
Minimal stand-in for the parts of dnspython this project uses.

It is installed ONLY when the real dnspython package is missing, so the tests
can still exercise our own logic. Run the tests with real dnspython installed
(pip install dnspython) for full confidence.
"""
import sys
import types


def install():
    exc = types.ModuleType("dns.exception")

    class DNSException(Exception):
        pass

    class Timeout(DNSException):
        pass

    exc.DNSException, exc.Timeout = DNSException, Timeout

    name = types.ModuleType("dns.name")

    class EmptyLabel(DNSException):
        pass

    class LabelTooLong(DNSException):
        pass

    class NameTooLong(DNSException):
        pass

    def from_text(text):
        if text in ("", "."):
            return text
        labels = text.rstrip(".").split(".")
        if any(label == "" for label in labels):
            raise EmptyLabel("empty label")
        if any(len(label) > 63 for label in labels):
            raise LabelTooLong("label too long")
        if len(text) > 253:
            raise NameTooLong("name too long")
        return text

    name.EmptyLabel, name.LabelTooLong, name.NameTooLong = EmptyLabel, LabelTooLong, NameTooLong
    name.from_text = from_text

    res = types.ModuleType("dns.resolver")

    class NXDOMAIN(DNSException):
        pass

    class NoAnswer(DNSException):
        pass

    class NoNameservers(DNSException):
        pass

    class NoResolverConfiguration(DNSException):
        pass

    class Resolver:
        def __init__(self, configure=True):
            self.nameservers = ["192.0.2.53"] if configure else []
            self.lifetime = None

        def resolve(self, qname, rdtype):
            raise NotImplementedError

    for cls in (NXDOMAIN, NoAnswer, NoNameservers, NoResolverConfiguration, Resolver):
        setattr(res, cls.__name__, cls)

    pkg = types.ModuleType("dns")
    pkg.exception, pkg.name, pkg.resolver = exc, name, res
    sys.modules.update({"dns": pkg, "dns.exception": exc, "dns.name": name, "dns.resolver": res})
