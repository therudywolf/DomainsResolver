"""Tests for pipeline read_and_classify, cache, and --dry-run."""
import json
import os
import sys

import pytest

from pipeline import (
    read_and_classify,
    load_domain_cache,
    save_domain_cache,
    main_sync,
)


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


class TestLoadDomainCache:
    def test_missing_path_returns_empty(self):
        assert load_domain_cache("/nonexistent/cache.json") == {}

    def test_empty_file_returns_empty(self, tmp_path):
        p = tmp_path / "cache.json"
        p.write_text("")
        assert load_domain_cache(str(p)) == {}

    def test_valid_json_returns_dict(self, tmp_path):
        p = tmp_path / "cache.json"
        data = {"example.com": {"ips": ["1.2.3.4"], "ts": 12345}}
        p.write_text(json.dumps(data))
        assert load_domain_cache(str(p)) == data

    def test_invalid_json_returns_empty(self, tmp_path):
        p = tmp_path / "cache.json"
        p.write_text("{ invalid")
        assert load_domain_cache(str(p)) == {}

    def test_non_dict_json_returns_empty(self, tmp_path):
        p = tmp_path / "cache.json"
        p.write_text("[1, 2, 3]")
        assert load_domain_cache(str(p)) == {}


class TestSaveDomainCache:
    def test_writes_and_replaces_atomically(self, tmp_path):
        p = tmp_path / "cache.json"
        cache = {"a.com": {"ips": ["1.2.3.4"], "ts": 1}}
        save_domain_cache(str(p), cache)
        assert p.exists()
        assert json.loads(p.read_text()) == cache
        assert not (tmp_path / "cache.json.tmp").exists()

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "cache.json"
        p.write_text('{"old": {}}')
        save_domain_cache(str(p), {"new": {"ips": [], "ts": 0}})
        assert json.loads(p.read_text()) == {"new": {"ips": [], "ts": 0}}


class TestMainSyncDryRun:
    def test_dry_run_exits_zero_and_writes_no_output(self, tmp_path, monkeypatch):
        input_f = tmp_path / "input.txt"
        input_f.write_text("1.2.3.4\n10.0.0.0/8\n")
        output_f = tmp_path / "output.txt"
        monkeypatch.setattr("pipeline.INPUT_FILE", str(input_f))
        monkeypatch.setattr("pipeline.OUTPUT_FILE", str(output_f))
        monkeypatch.setattr(sys, "argv", ["pipeline", "--dry-run"])
        import pipeline as pl
        pl.main_sync()
        assert not output_f.exists()

    def test_dry_run_with_missing_input_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.INPUT_FILE", str(tmp_path / "nonexistent.txt"))
        monkeypatch.setattr(sys, "argv", ["pipeline", "--dry-run"])
        import pipeline as pl
        with pytest.raises(SystemExit) as exc_info:
            pl.main_sync()
        assert exc_info.value.code != 0
