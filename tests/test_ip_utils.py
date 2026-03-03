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
        assert optimize_list([]) == []

    def test_dedup_ips(self):
        raw = ["1.2.3.4", "1.2.3.4", "5.6.7.8"]
        out = optimize_list(raw)
        assert "1.2.3.4" in out
        assert "5.6.7.8" in out
        assert out.count("1.2.3.4") == 1

    def test_subnet_contains_ip(self):
        raw = ["192.168.1.0/24", "192.168.1.10"]
        out = optimize_list(raw)
        assert "192.168.0.0/24" in out or "192.168.1.0/24" in out
        assert "192.168.1.10" not in out

    def test_invalid_skipped(self):
        raw = ["1.2.3.4", "garbage", "5.6.7.8"]
        out = optimize_list(raw)
        assert len(out) == 2
        assert "1.2.3.4" in out
        assert "5.6.7.8" in out

    def test_sorted(self):
        raw = ["10.0.0.1", "1.1.1.1", "192.168.1.1"]
        out = optimize_list(raw)
        # Result should be sorted (ip_utils sorts by address then prefix)
        addrs = [ip_address(x) for x in out]
        assert addrs == sorted(addrs)
