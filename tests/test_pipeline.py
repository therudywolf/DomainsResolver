"""Tests for pipeline read_and_classify, parse_dot_servers and --dry-run."""
import os
import tempfile
from pathlib import Path

import pytest

from pipeline import read_and_classify, parse_dot_servers


class TestParseDotServers:
    """Tests for DNS over TLS server list parsing."""

    def test_parses_valid_dot_servers(self):
        s = "45.90.28.61:DMTCDRK-67bd84.dns.nextdns.io,45.90.30.61:DMTCDRK-67bd84.dns.nextdns.io"
        result = parse_dot_servers(s)
        assert len(result) == 2
        assert result[0].address == "45.90.28.61"
        assert result[0].port == 853
        assert result[0].hostname == "DMTCDRK-67bd84.dns.nextdns.io"
        assert result[1].address == "45.90.30.61"
        assert result[1].hostname == "DMTCDRK-67bd84.dns.nextdns.io"

    def test_empty_string_returns_empty_list(self):
        assert parse_dot_servers("") == []
        assert parse_dot_servers("   ") == []

    def test_invalid_format_no_colon_skipped(self):
        result = parse_dot_servers("8.8.8.8,1.1.1.1")
        assert result == []

    def test_single_server(self):
        result = parse_dot_servers("1.2.3.4:dot.example.com")
        assert len(result) == 1
        assert result[0].address == "1.2.3.4"
        assert result[0].hostname == "dot.example.com"

    def test_whitespace_trimmed(self):
        result = parse_dot_servers("  1.2.3.4 : dot.example.com  ,  5.6.7.8 : dot2.example.com  ")
        assert len(result) == 2
        assert result[0].address == "1.2.3.4"
        assert result[0].hostname == "dot.example.com"
        assert result[1].address == "5.6.7.8"
        assert result[1].hostname == "dot2.example.com"


class TestReadAndClassify:
    def test_classifies_ip_and_cidr(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("192.168.1.1\n10.0.0.0/8\n")
        ip_cidr, domains = read_and_classify(str(f))
        assert len(domains) == 0
        assert "192.168.1.1" in ip_cidr
        assert "10.0.0.0/8" in ip_cidr

    def test_classifies_domains(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("example.com\n*.test.com\n")
        ip_cidr, domains = read_and_classify(str(f))
        assert len(ip_cidr) == 0
        assert "example.com" in domains
        assert "*.test.com" in domains

    def test_skips_comments_and_empty(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("# comment\n\n1.2.3.4\n\n")
        ip_cidr, domains = read_and_classify(str(f))
        assert ip_cidr == ["1.2.3.4"]
        assert domains == []

    def test_dedup_and_normalize_domains(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("Example.COM\nexample.com\n")
        ip_cidr, domains = read_and_classify(str(f))
        assert len(domains) == 1
        assert domains[0] == "example.com"

    def test_missing_file_exits(self):
        with pytest.raises(SystemExit):
            read_and_classify("/nonexistent/path/input.txt")
