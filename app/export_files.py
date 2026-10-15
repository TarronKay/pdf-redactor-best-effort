# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Reserve and write a numbered PDF/verification pair without overwriting.

Windows keeps a separate ownership handle until commit. Cleanup marks only
that created file object for deletion, even if a write/close operation fails.
No existing object is opened for writing or deleted.
"""
import ctypes,errno,itertools,json,os
from pathlib import Path
from typing import NamedTuple

class SavedPair(NamedTuple):
    pdf_path:Path
    report_path:Path

if os.name=='nt':
    import msvcrt
    from ctypes import wintypes as w
    _kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    _kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
    _kernel.CreateFileW.restype=w.HANDLE
    _kernel.GetCurrentProcess.restype=w.HANDLE
    _kernel.DuplicateHandle.argtypes=[w.HANDLE,w.HANDLE,w.HANDLE,ctypes.POINTER(w.HANDLE),w.DWORD,w.BOOL,w.DWORD]
    _kernel.DuplicateHandle.restype=w.BOOL
    _kernel.CloseHandle.argtypes=[w.HANDLE];_kernel.CloseHandle.restype=w.BOOL
    _kernel.SetFileInformationByHandle.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
    _kernel.SetFileInformationByHandle.restype=w.BOOL
    class _Disposition(ctypes.Structure):_fields_=[('delete',ctypes.c_ubyte)]
    def _delete_handle(handle):
        disposition=_Disposition(True)
        if not _kernel.SetFileInformationByHandle(handle,4,ctypes.byref(disposition),ctypes.sizeof(disposition)):
            raise ctypes.WinError(ctypes.get_last_error())

class _Reservation:
    def __init__(self,path,file,guard):
        self.path=path;self.file=file;self.guard=guard
    def close_writer(self):self.file.close()
    def close_guard(self):
        if self.guard is None:return
        guard=self.guard;self.guard=None
        _kernel.CloseHandle(guard)
    def discard(self):
        try:
            _delete_handle(self.guard)
        finally:
            try:self.close_writer()
            finally:self.close_guard()

def _reserve(path):
    if os.name!='nt':raise OSError('Race-safe pair export requires Windows file-ownership handles in this candidate.')
    if os.name=='nt':
        # CREATE_NEW is the authority; prechecks are only a fast skip.
        # Share read only: other writers/renames/deletes cannot replace the
        # created object while our ownership handle is live.
        guard=_kernel.CreateFileW(str(path.absolute()),0x40000000|0x10000,1,None,1,0x80,None)
        if guard==ctypes.c_void_p(-1).value:
            error=ctypes.get_last_error()
            if error in {80,183}:raise FileExistsError(errno.EEXIST,'Export name already exists',str(path))
            raise ctypes.WinError(error)
        duplicate=w.HANDLE();process=_kernel.GetCurrentProcess();fd=None
        try:
            if not _kernel.DuplicateHandle(process,guard,process,ctypes.byref(duplicate),0,False,2):
                raise ctypes.WinError(ctypes.get_last_error())
            fd=msvcrt.open_osfhandle(duplicate.value,os.O_WRONLY|os.O_BINARY)
            duplicate=w.HANDLE() # descriptor now owns this handle
            file=os.fdopen(fd,'wb');fd=None
            return _Reservation(path,file,guard)
        except BaseException:
            try:_delete_handle(guard)
            finally:
                if fd is not None:os.close(fd)
                if duplicate.value:_kernel.CloseHandle(duplicate)
                _kernel.CloseHandle(guard)
            raise

def _cleanup(created):
    errors=[]
    for reservation in reversed(created):
        try:reservation.discard()
        except OSError as error:errors.append(error)
    if errors:raise errors[0]

def write_new_pair(destination,pdf,report):
    """Use the base name or first free -N pair; return both actual paths."""
    if os.name!='nt':raise OSError('Race-safe pair export requires Windows file-ownership handles in this candidate.')
    destination=Path(destination)
    if destination.suffix.lower()!='.pdf':raise ValueError('Choose a .pdf destination.')
    report_bytes=json.dumps(report,indent=2).encode('utf-8')
    for number in itertools.count():
        candidate=destination if number==0 else destination.with_name(f'{destination.stem}-{number}{destination.suffix}')
        report_path=candidate.with_suffix('.verification.json')
        if os.path.lexists(candidate) or os.path.lexists(report_path):continue
        created=[]
        try:
            created.append(_reserve(candidate))
            created.append(_reserve(report_path))
        except FileExistsError:
            _cleanup(created);continue
        except BaseException:
            _cleanup(created);raise
        try:
            for reservation,payload in zip(created,[pdf,report_bytes]):
                reservation.file.write(payload)
                reservation.file.flush()
                os.fsync(reservation.file.fileno())
            for reservation in created:reservation.close_writer()
        except BaseException:
            _cleanup(created);raise
        for reservation in created:reservation.close_guard()
        return SavedPair(candidate,report_path)
