"""Packaging regression checks without launching windows or processes."""
import importlib.util,json,subprocess,sys
from pathlib import Path
import pytest

def controller():
 path=Path(__file__).resolve().parents[1]/'app/best_effort_controller.py'
 spec=importlib.util.spec_from_file_location('release_controller',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def test_frozen_dispatch_is_absolute_hidden_worker_with_real_pipes(tmp_path,monkeypatch):
 module=controller();worker=tmp_path/'PDFRedactorWorker.exe';worker.touch()
 monkeypatch.setattr(sys,'frozen',True,raising=False);monkeypatch.setattr(sys,'executable',str(tmp_path/'PDFRedactor.exe'))
 calls=[]
 def run(command,**kw):calls.append((command,kw));return subprocess.CompletedProcess(command,0,json.dumps(dict(ok=True,result=dict(verified=True))).encode())
 monkeypatch.setattr(module.subprocess,'run',run)
 assert module.call_best_effort_worker(b'','health')==dict(verified=True)
 command,kw=calls[0];assert command==[str(worker.resolve())] and kw['cwd']==str(tmp_path)
 assert kw['timeout']==60 and kw['stdout']==subprocess.PIPE and kw['stderr']==subprocess.DEVNULL and kw['creationflags']==subprocess.CREATE_NO_WINDOW

def test_missing_frozen_worker_fails_without_relaunching_gui(tmp_path,monkeypatch):
 module=controller();monkeypatch.setattr(sys,'frozen',True,raising=False);monkeypatch.setattr(sys,'executable',str(tmp_path/'PDFRedactor.exe'))
 monkeypatch.setattr(module.subprocess,'run',lambda *a,**kw:pytest.fail('Must not start a missing worker or GUI'))
 with pytest.raises(ValueError,match='worker is missing'):module.call_best_effort_worker(b'','health')

def test_worker_timeout_never_returns_success(tmp_path,monkeypatch):
 module=controller();(tmp_path/'PDFRedactorWorker.exe').touch()
 monkeypatch.setattr(sys,'frozen',True,raising=False);monkeypatch.setattr(sys,'executable',str(tmp_path/'PDFRedactor.exe'))
 def expired(*a,**kw):raise subprocess.TimeoutExpired(a[0],60)
 monkeypatch.setattr(module.subprocess,'run',expired)
 with pytest.raises(ValueError,match='60 seconds; nothing was saved'):module.call_best_effort_worker(b'','export',regions=[])
