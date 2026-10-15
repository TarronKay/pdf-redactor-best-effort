# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Worker resource limits; no legacy processing entry point."""
import os
def limit_memory():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes as w
        class BASIC(ctypes.Structure):
            _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',w.DWORD),('min_work',ctypes.c_size_t),('max_work',ctypes.c_size_t),('active',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(n,ctypes.c_uint64) for n in ['read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes']]
        class EXT(ctypes.Structure):
            _fields_=[('basic',BASIC),('io',IO),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateJobObjectW.restype=w.HANDLE
        kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR]
        kernel.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        kernel.GetCurrentProcess.restype=w.HANDLE
        global _JOB
        _JOB=kernel.CreateJobObjectW(None,None)
        settings=EXT(); settings.basic.flags=0x100 | 0x2
        settings.basic.process_time=45*10_000_000
        settings.process_memory=768*1024*1024
        if not _JOB or not kernel.SetInformationJobObject(_JOB,9,ctypes.byref(settings),ctypes.sizeof(settings)) or not kernel.AssignProcessToJobObject(_JOB,kernel.GetCurrentProcess()):
            raise RuntimeError('Worker resource limits unavailable; processing blocked.')
        kernel.QueryInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.c_void_p]
        actual=EXT()
        if not kernel.QueryInformationJobObject(_JOB,9,ctypes.byref(actual),ctypes.sizeof(actual),None):
            raise RuntimeError('Worker resource limits could not be verified.')
        if actual.process_memory!=settings.process_memory or actual.basic.process_time!=settings.basic.process_time or actual.basic.flags & 0x102 != 0x102:
            raise RuntimeError('Worker resource limits did not match the required policy.')
        return dict(memory_bytes=actual.process_memory,cpu_seconds=actual.basic.process_time/10_000_000,flags=actual.basic.flags,verified_job_object=True)
    else:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(45,45))
