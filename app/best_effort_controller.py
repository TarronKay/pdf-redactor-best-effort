# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
import base64,json,subprocess,sys
from pathlib import Path

def call_best_effort_worker(data,op,**kwargs):
    try:
        if getattr(sys,'frozen',False):
            worker=Path(sys.executable).resolve().with_name('PDFRedactorWorker.exe')
            if not worker.is_file():raise ValueError('The installed processing worker is missing. Repair or reinstall the app.')
            command=[str(worker)];directory=worker.parent
        else:command=[sys.executable,'-m','best_effort_worker'];directory=Path(__file__).resolve().parent
        result=subprocess.run(command,cwd=str(directory),input=json.dumps(dict(data=base64.b64encode(data).decode(),op=op,**kwargs)).encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0)
        if result.returncode or not result.stdout:raise ValueError('PDF worker failed or exceeded local resource bounds.')
        response=json.loads(result.stdout)
        if not response['ok']:raise ValueError(response['error'])
        return response['result']
    except subprocess.TimeoutExpired:raise ValueError('Processing exceeded 60 seconds; nothing was saved.') from None
