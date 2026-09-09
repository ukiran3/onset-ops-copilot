"""Import this before making any HTTP calls.

This sandbox blackholes outbound IPv6 (packets are silently dropped rather
than rejected), and DNS resolvers here return IPv6 addresses first. Python's
default connection logic tries addresses in order and blocks through a full
OS-level TCP connect timeout (tens of seconds) per dead IPv6 address before
falling back to IPv4 -- unlike curl, which races both via Happy Eyeballs.
Forcing getaddrinfo to IPv4-only avoids that multi-minute stall.
"""

import socket

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)


socket.getaddrinfo = _ipv4_only_getaddrinfo
