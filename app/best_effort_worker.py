# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
import base64,json,sys
from resource_limits import limit_memory

def main():
    try:
        limits=limit_memory()
        from best_effort_engine import analyze,preview,prepare_previews,export,Rejected
        raw=sys.stdin.buffer.read(32*1024*1024+1)
        if len(raw)>32*1024*1024:raise Rejected('Request exceeds the local input limit.')
        request=json.loads(raw);data=base64.b64decode(request['data'],validate=True);op=request['op']
        mode=request.get('mode','best-effort-raster');options=request.get('options',{})
        if op=='health':
            import os,pymupdf
            result=dict(version='0.9.2',frozen=bool(getattr(sys,'frozen',False)),pid=os.getpid(),limits=limits,offline_processing=True,native_engine_version=pymupdf.mupdf_version,wrapper_version=pymupdf.pymupdf_version,application_license='AGPL-3.0-only')
        elif op=='analyze':result=analyze(data,**options)
        elif op=='preview':
            result=preview(data,request['page'],request.get('regions'),mode);result['png']=base64.b64encode(result['png']).decode()
        elif op=='prepare_previews':
            result=prepare_previews(data,request['regions'],options,mode);result['pages']=[base64.b64encode(p).decode() for p in result['pages']]
        elif op=='export':
            payload,report=export(data,request['regions'],options,mode,request.get('checked',[]),request.get('expected_output_sha256'))
            result=dict(pdf=base64.b64encode(payload).decode(),report=report)
        else:raise Rejected('Unknown operation.')
        print(json.dumps(dict(ok=True,result=result)))
    except Exception as error:
        from engine import Rejected
        print(json.dumps(dict(ok=False,error=str(error) if isinstance(error,Rejected) else 'Processing failed or exceeded local resource bounds. Nothing was saved.')))

if __name__=='__main__':main()
