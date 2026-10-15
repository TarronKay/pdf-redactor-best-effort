import concurrent.futures,json,os
from pathlib import Path
import pytest
import export_files as e

@pytest.mark.parametrize('existing',[[],['pdf'],['json'],['pdf','json']])
def test_no_collision_or_either_pair_member_existing(tmp_path,existing):
    target=tmp_path/'result.pdf';report=target.with_suffix('.verification.json');before={}
    for kind in existing:
        path=target if kind=='pdf' else report;path.write_bytes(('original-'+kind).encode());before[path]=path.read_bytes()
    saved=e.write_new_pair(target,b'new-pdf',{'new':'report'})
    stem='result' if not existing else 'result-1'
    assert saved.pdf_path.name==stem+'.pdf' and saved.report_path.name==stem+'.verification.json'
    assert saved.pdf_path.read_bytes()==b'new-pdf' and json.loads(saved.report_path.read_text())=={'new':'report'}
    assert all(p.read_bytes()==content for p,content in before.items())
    if existing==['json']:assert not target.exists()
    if existing==['pdf']:assert not report.exists()

def test_first_free_gap_requires_both_names_available(tmp_path):
    paths=[tmp_path/'score.pdf',tmp_path/'score-1.verification.json',tmp_path/'score-3.pdf',tmp_path/'score-4.verification.json']
    for p in paths:p.write_bytes(b'preserve')
    saved=e.write_new_pair(tmp_path/'score.pdf',b'new',{})
    assert saved.pdf_path.name=='score-2.pdf' and saved.report_path.name=='score-2.verification.json'
    assert all(p.read_bytes()==b'preserve' for p in paths)

@pytest.mark.parametrize('kind',['pdf','json'])
def test_competing_creation_between_precheck_and_reservation(tmp_path,monkeypatch,kind):
    target=tmp_path/'race.pdf';report=target.with_suffix('.verification.json');race=target if kind=='pdf' else report
    original=e._reserve;triggered=[]
    def reserve(path):
        if path==race and not triggered:
            race.write_bytes(b'competing-owner');triggered.append(True)
        return original(path)
    monkeypatch.setattr(e,'_reserve',reserve)
    saved=e.write_new_pair(target,b'ours',{'owner':'ours'})
    assert race.read_bytes()==b'competing-owner'
    assert saved.pdf_path.name=='race-1.pdf' and saved.report_path.name=='race-1.verification.json'
    if kind=='json':assert not target.exists() # only our failed PDF reservation removed

def test_report_claim_failure_removes_only_owned_pdf(tmp_path,monkeypatch):
    target=tmp_path/'fail.pdf';unrelated=tmp_path/'keep.pdf';unrelated.write_bytes(b'keep')
    original=e._reserve
    def reserve(path):
        if path.suffix=='.json':raise PermissionError('synthetic report-claim failure')
        return original(path)
    monkeypatch.setattr(e,'_reserve',reserve)
    with pytest.raises(PermissionError):e.write_new_pair(target,b'ours',{})
    assert not target.exists() and not target.with_suffix('.verification.json').exists()
    assert unrelated.read_bytes()==b'keep'

@pytest.mark.parametrize('member',['pdf','json'])
def test_partial_write_failure_cleans_owned_pair(tmp_path,monkeypatch,member):
    target=tmp_path/'fail.pdf';keep=tmp_path/'keep.verification.json';keep.write_bytes(b'keep')
    original=e._reserve
    class FailFile:
        def __init__(self,file):self.file=file
        def write(self,payload):self.file.write(payload[:2]);self.file.flush();raise OSError('synthetic partial write failure')
        def close(self):self.file.close()
    def reserve(path):
        reservation=original(path)
        if (member=='pdf' and path.suffix=='.pdf') or (member=='json' and path.suffix=='.json'):reservation.file=FailFile(reservation.file)
        return reservation
    monkeypatch.setattr(e,'_reserve',reserve)
    with pytest.raises(OSError,match='partial write'):e.write_new_pair(target,b'ours',{'record':'ours'})
    assert set(tmp_path.iterdir())=={keep} and keep.read_bytes()==b'keep'

def test_concurrent_exports_reserve_distinct_matching_pairs(tmp_path):
    target=tmp_path/'parallel.pdf'
    def save(i):return i,e.write_new_pair(target,f'pdf-{i}'.encode(),{'owner':i})
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(save,range(12)))
    assert len({saved.pdf_path for _,saved in results})==12
    for i,saved in results:
        assert saved.pdf_path.read_bytes()==f'pdf-{i}'.encode()
        assert json.loads(saved.report_path.read_text())=={'owner':i}
        assert saved.pdf_path.stem==saved.report_path.name.removesuffix('.verification.json')
    assert len(list(tmp_path.iterdir()))==24

def test_uppercase_pdf_name_and_serialization_failure(tmp_path):
    target=tmp_path/'Report.PDF';target.write_bytes(b'keep')
    saved=e.write_new_pair(target,b'ours',{});assert saved.pdf_path.name=='Report-1.PDF'
    before=set(tmp_path.iterdir())
    with pytest.raises(TypeError):e.write_new_pair(tmp_path/'bad.pdf',b'ours',{'bad':object()})
    assert set(tmp_path.iterdir())==before and target.read_bytes()==b'keep'
