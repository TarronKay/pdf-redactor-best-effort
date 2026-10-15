"""Independent ownership, contention and partial-failure export tests."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest
import export_files as exports


def test_either_existing_path_skips_whole_pair_and_preserves_gaps(tmp_path):
    destination = tmp_path / 'result.pdf'
    (tmp_path / 'result.verification.json').write_bytes(b'existing-base-report')
    (tmp_path / 'result-1.pdf').write_bytes(b'existing-numbered-pdf')
    (tmp_path / 'result-3.pdf').write_bytes(b'existing-later-pdf')
    pair = exports.write_new_pair(destination, b'new-pdf', {'owner': 'new'})
    assert pair.pdf_path.name == 'result-2.pdf'
    assert pair.report_path.name == 'result-2.verification.json'
    assert pair.pdf_path.read_bytes() == b'new-pdf'
    assert json.loads(pair.report_path.read_text()) == {'owner': 'new'}
    assert (tmp_path / 'result.verification.json').read_bytes() == b'existing-base-report'
    assert (tmp_path / 'result-1.pdf').read_bytes() == b'existing-numbered-pdf'
    assert (tmp_path / 'result-3.pdf').read_bytes() == b'existing-later-pdf'


def test_competing_exports_get_distinct_complete_pairs(tmp_path):
    barrier = threading.Barrier(6)
    def export(number):
        barrier.wait(timeout=10)
        return number, exports.write_new_pair(tmp_path / 'shared.pdf', f'PDF-{number}'.encode(), {'number': number})
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(export, range(6)))
    assert len({pair.pdf_path for number, pair in results}) == 6
    assert len(list(tmp_path.iterdir())) == 12
    for number, pair in results:
        assert pair.pdf_path.read_bytes() == f'PDF-{number}'.encode()
        assert json.loads(pair.report_path.read_text()) == {'number': number}
        assert pair.report_path == pair.pdf_path.with_suffix('.verification.json')


def test_second_path_race_preserves_other_actors_file(tmp_path, monkeypatch):
    original = exports._reserve
    raced = False
    def reserve(path):
        nonlocal raced
        if path.name == 'race.verification.json' and not raced:
            raced = True
            path.write_bytes(b'foreign-report')
        return original(path)
    monkeypatch.setattr(exports, '_reserve', reserve)
    pair = exports.write_new_pair(tmp_path / 'race.pdf', b'ours', {})
    assert pair.pdf_path.name == 'race-1.pdf'
    assert not (tmp_path / 'race.pdf').exists()
    assert (tmp_path / 'race.verification.json').read_bytes() == b'foreign-report'


def test_reservation_error_removes_only_created_first_path(tmp_path, monkeypatch):
    original = exports._reserve
    (tmp_path / 'keep.txt').write_bytes(b'keep')
    def reserve(path):
        if path.suffix == '.json':
            raise PermissionError('synthetic second reservation failure')
        return original(path)
    monkeypatch.setattr(exports, '_reserve', reserve)
    with pytest.raises(PermissionError):
        exports.write_new_pair(tmp_path / 'partial.pdf', b'ours', {})
    assert sorted(p.name for p in tmp_path.iterdir()) == ['keep.txt']
    assert (tmp_path / 'keep.txt').read_bytes() == b'keep'


@pytest.mark.parametrize('failure', ['flush', 'fsync', 'close'])
def test_partial_io_failure_cleans_created_pair_only(tmp_path, monkeypatch, failure):
    (tmp_path / 'already.pdf').write_bytes(b'already-pdf')
    (tmp_path / 'already.verification.json').write_bytes(b'already-report')
    original = exports._reserve
    class Fault:
        def __init__(self, inner): self.inner = inner; self.failed = False
        def write(self, payload): return self.inner.write(payload)
        def fileno(self): return self.inner.fileno()
        def flush(self):
            self.inner.flush()
            if failure == 'flush' and not self.failed:
                self.failed = True
                raise OSError('synthetic flush failure after bytes written')
        def close(self):
            self.inner.close()
            if failure == 'close' and not self.failed:
                self.failed = True
                raise OSError('synthetic close failure after writer closed')
    def reserve(path):
        result = original(path)
        if path.suffix == '.json': result.file = Fault(result.file)
        return result
    monkeypatch.setattr(exports, '_reserve', reserve)
    if failure == 'fsync':
        monkeypatch.setattr(exports.os, 'fsync', lambda fd: (_ for _ in ()).throw(OSError('synthetic fsync failure')))
    with pytest.raises(OSError):
        exports.write_new_pair(tmp_path / 'already.pdf', b'new', {})
    assert sorted(p.name for p in tmp_path.iterdir()) == ['already.pdf', 'already.verification.json']
    assert (tmp_path / 'already.pdf').read_bytes() == b'already-pdf'
    assert (tmp_path / 'already.verification.json').read_bytes() == b'already-report'


@pytest.mark.skipif(os.name != 'nt', reason='Windows ownership-handle contract')
def test_windows_reserved_path_cannot_be_replaced_during_failure(tmp_path, monkeypatch):
    original = exports._reserve
    replacement = tmp_path / 'foreign.txt'
    replacement.write_bytes(b'foreign-safe')
    attempts = []
    class Fault:
        def __init__(self, inner, path): self.inner = inner; self.path = path
        def write(self, payload):
            self.inner.write(payload)
            with pytest.raises(PermissionError): os.replace(replacement, self.path)
            attempts.append(self.path)
            raise OSError('synthetic write failure')
        def close(self): self.inner.close()
    def reserve(path):
        result = original(path)
        if path.suffix == '.pdf': result.file = Fault(result.file, path)
        return result
    monkeypatch.setattr(exports, '_reserve', reserve)
    with pytest.raises(OSError): exports.write_new_pair(tmp_path / 'guard.pdf', b'new', {})
    assert attempts
    assert replacement.read_bytes() == b'foreign-safe'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['foreign.txt']


def test_unserializable_report_creates_nothing(tmp_path):
    with pytest.raises(TypeError):
        exports.write_new_pair(tmp_path / 'none.pdf', b'new', {'bad': object()})
    assert list(tmp_path.iterdir()) == []


def test_unsupported_platform_rejects_both_entrypoints_without_creation(tmp_path, monkeypatch):
    existing = tmp_path / 'keep.pdf'
    existing.write_bytes(b'preserve-existing')
    destination = tmp_path / 'unsupported.pdf'
    # Replace only this module's namespace; mutating the shared os.name would
    # make pathlib/pytest try unsupported PosixPath objects on Windows.
    with monkeypatch.context() as local:
        local.setattr(exports, 'os', SimpleNamespace(name='posix'))
        with pytest.raises(OSError, match='requires Windows file-ownership handles'):
            exports.write_new_pair(destination, b'new', {})
        with pytest.raises(OSError, match='requires Windows file-ownership handles'):
            exports._reserve(destination)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['keep.pdf']
    assert existing.read_bytes() == b'preserve-existing'
