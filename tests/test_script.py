"""Tests for script.extract_ips_and_cidrs."""
import pytest

from script import extract_ips_and_cidrs


class TestExtractIpsAndCidrs:
    def test_extracts_ips_and_cidrs(self, tmp_path):
        f = tmp_path / "input.txt"
        f.write_text("192.168.1.1\n10.0.0.0/8\n1.2.3.4\n")
        result = extract_ips_and_cidrs(str(f))
        assert "192.168.1.1" in result
        assert "10.0.0.0/8" in result
        assert "1.2.3.4" in result
        assert len(result) == 3

    def test_empty_file_returns_empty_list(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        assert extract_ips_and_cidrs(str(f)) == []

    def test_no_ips_returns_empty_list(self, tmp_path):
        f = tmp_path / "no_ips.txt"
        f.write_text("hello\nworld\nexample.com\n")
        assert extract_ips_and_cidrs(str(f)) == []

    def test_mixed_content_extracts_only_ips(self, tmp_path):
        f = tmp_path / "mixed.txt"
        f.write_text("prefix 1.2.3.4 suffix\n10.0.0.0/8 and 192.168.1.1\n")
        result = extract_ips_and_cidrs(str(f))
        assert "1.2.3.4" in result
        assert "10.0.0.0/8" in result
        assert "192.168.1.1" in result
        assert len(result) == 3

    def test_missing_file_returns_empty_list(self):
        result = extract_ips_and_cidrs("/nonexistent/path/file.txt")
        assert result == []
