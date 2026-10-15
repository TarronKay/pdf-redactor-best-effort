# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""One verified, memory-only Best Effort preview set, bound to all input state."""
import hashlib,json,threading

def cache_key(data,regions,options,mode):
    state=dict(version=1,source_sha256=hashlib.sha256(data).hexdigest(),regions=regions,options=options,mode=mode)
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

class PreviewCache:
    def __init__(self):
        self._lock=threading.Lock();self._generation=0;self._key=None;self._result=None
    def clear(self):
        with self._lock:
            self._generation+=1;self._key=None;self._result=None
    def peek(self,data,regions,options,mode):
        key=cache_key(data,regions,options,mode)
        with self._lock:
            return self._result if self._key==key else None
    def get(self,data,regions,options,mode,prepare):
        # Freeze the mutable request before hashing/dispatch; source is bytes.
        regions=json.loads(json.dumps(regions,allow_nan=False))
        options=json.loads(json.dumps(options,allow_nan=False))
        key=cache_key(data,regions,options,mode)
        with self._lock:
            if self._key==key and self._result is not None:return self._result
            self._generation+=1;generation=self._generation
            self._key=key;self._result=None
        result=prepare(data,regions,options)
        if result.get('cache_key')!=key or not result.get('output_sha256') or not isinstance(result.get('pages'),list) or not 1<=len(result['pages'])<=30 or any(not isinstance(p,str) for p in result['pages']) or sum(map(len,result['pages']))>96*1024*1024:
            raise ValueError('Invalid or oversized verified preview set.')
        with self._lock:
            if generation!=self._generation or self._key!=key:raise ValueError('Preview settings changed; render a fresh preview.')
            self._result=result
        return result
