"""Tests for ip_utils."""
import pytest
from ipaddress import ip_address, ip_network

from ip_utils import is_valid_ip, optimize_list, parse_entry


class TestIsValidIp:
    def test_valid_ips(self):
        assert is_valid_ip("0.0.0.0") is True
        assert is_valid_ip("255.255.255.255") is True
        assert is_valid_ip("192.168.1.1") is True

    def test_invalid_ips(self):
        assert is_valid_ip("") is False
        assert is_valid_ip("256.0.0.0") is False
        assert is_valid_ip("1.2.3") is False
        assert is_valid_ip("1.2.3.4.5") is False
        assert is_valid_ip("x.1.1.1") is False


class TestParseEntry:
    def test_empty_or_whitespace(self):
        assert parse_entry("") is None
        assert parse_entry("   ") is None

    def test_valid_ip(self):
        assert parse_entry("192.168.1.1") == ip_address("192.168.1.1")
        assert parse_entry("  10.0.0.1  ") == ip_address("10.0.0.1")

    def test_valid_cidr(self):
        assert parse_entry("192.168.0.0/24") == ip_network("192.168.0.0/24")
        assert parse_entry("10.0.0.0/8") == ip_network("10.0.0.0/8")

    def test_invalid_returns_none(self):
        assert parse_entry("not-an-ip") is None
        assert parse_entry("192.168.1.1/33") is None
        assert parse_entry("192.168.1.1/99") is None
        assert parse_entry("300.1.1.1") is None


class TestOptimizeList:
    def test_empty(self):
        assert optimize_list([], quiet=True) == []

    def test_dedup_ips(self):
        raw = ["1.2.3.4", "1.2.3.4", "5.6.7.8"]
        out = optimize_list(raw, collapse_ips=False, quiet=True)
        assert "1.2.3.4" in out
        assert "5.6.7.8" in out
        assert out.count("1.2.3.4") == 1

    def test_subnet_contains_ip(self):
        raw = ["192.168.1.0/24", "192.168.1.10"]
        out = optimize_list(raw, quiet=True)
        assert "192.168.0.0/24" in out or "192.168.1.0/24" in out
        assert "192.168.1.10" not in out

    def test_invalid_skipped(self):
        raw = ["1.2.3.4", "garbage", "5.6.7.8"]
        out = optimize_list(raw, collapse_ips=False, quiet=True)
        assert len(out) == 2
        assert "1.2.3.4" in out
        assert "5.6.7.8" in out

    def test_sorted(self):
        raw = ["10.0.0.1", "1.1.1.1", "192.168.1.1"]
        out = optimize_list(raw, collapse_ips=False, quiet=True)
        # Result should be sorted (ip_utils sorts by address then prefix)
        addrs = [ip_address(x) for x in out]
        assert addrs == sorted(addrs)

    def test_reserved_filtered_by_default(self):
        """0.0.0.0, 127.0.0.1, 255.255.255.255 and 0.0.0.0/8 excluded when filter_reserved=True."""
        raw = ["0.0.0.0", "127.0.0.1", "255.255.255.255", "1.2.3.4", "0.0.0.0/8"]
        out = optimize_list(raw, filter_reserved=True, collapse_ips=False, quiet=True)
        assert "1.2.3.4" in out
        assert "0.0.0.0" not in out
        assert "127.0.0.1" not in out
        assert "255.255.255.255" not in out
        assert not any(e.startswith("0.0.0.0") for e in out)
        assert not any("127." in e for e in out)

    def test_reserved_kept_when_filter_disabled(self):
        raw = ["0.0.0.0", "1.2.3.4"]
        out = optimize_list(raw, filter_reserved=False, collapse_ips=False, quiet=True)
        assert "0.0.0.0" in out
        assert "1.2.3.4" in out

    def test_collapse_ips_same_subnet(self):
        """Several IPs in same /24 are merged into one subnet when collapse_ips=True."""
        raw = ["192.168.2.1", "192.168.2.2", "192.168.2.10", "192.168.2.254"]
        out = optimize_list(raw, collapse_ips=True, quiet=True)
        assert len(out) <= 4
        assert any("/" in e for e in out)
        assert any("192.168.2" in e for e in out)
        nets = [ip_network(e) for e in out if "/" in e]
        for ip_str in raw:
            addr = ip_address(ip_str)
            assert any(addr in n for n in nets), f"{ip_str} not covered"

    def test_private_filtered_when_filter_private_true(self):
        """10.0.0.1 (private) excluded, 8.8.8.8 (public) kept when filter_private=True."""
        raw = ["10.0.0.1", "8.8.8.8"]
        out = optimize_list(raw, filter_reserved=True, filter_private=True, collapse_ips=False, quiet=True)
        assert "8.8.8.8" in out
        assert "10.0.0.1" not in out
