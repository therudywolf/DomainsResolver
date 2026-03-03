"""Tests for pipeline read_and_classify and --dry-run."""
import os
import tempfile
from pathlib import Path

import pytest

from pipeline import read_and_classify


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
