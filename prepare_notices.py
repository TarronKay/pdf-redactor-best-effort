# SPDX-License-Identifier: AGPL-3.0-only
"""Copy legal texts only from the reviewed local notice packet."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parent
def main():
 source=ROOT/'notices';target=ROOT/'dist/PDFRedactor/ThirdPartyNotices'
 if target.exists():raise RuntimeError('Refusing to replace existing notice payload')
 rows=[];omitted=[]
 for p in sorted(source.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(source)
  if (p.suffix.lower()=='.json' or rel.as_posix()=='README.md' or p.name=='ATTRIBUTIONS-DRAFT.txt'
      or 'reference-only' in rel.parts or any(x.lower() in {'tests','test','text-rendering-tests'} for x in rel.parts)):
   omitted.append(rel.as_posix());continue
  out=target/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
  rows.append(dict(path=rel.as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 (target/'ATTRIBUTIONS.txt').write_text('''PDF Redactor 0.9.2 third-party credits

Original application: AGPL-3.0-only; see the application LICENSE and LICENSING.md.
Third-party code retains the copyrights and terms preserved in this directory.

This software is based in part on the work of the FreeType Team.
This software is based in part on the work of the Independent JPEG Group.
This software includes Raqm; see runtime-additions/Raqm-0.10.3-COPYING.txt.
The application uses PyMuPDF/MuPDF 1.28.2, CPython, Tcl/Tk, Pillow,
fontTools, pypdf and components incorporated by these projects. Complete
version-specific notices, including font and hyphenation texts, are retained.

The three Microsoft Visual C++ runtime DLLs retain separate component terms
in Microsoft/. These terms do not replace rights in the AGPL application.
The Windows 10/11 operating system supplies its Universal C Runtime.
''',encoding='utf-8')
 (ROOT/'installer-notice-manifest.json').write_text(json.dumps(dict(copied=rows,omitted_nonruntime_evidence=omitted),indent=2))
 print('Copied',len(rows),'reviewed notice files plus credits')
if __name__=='__main__':main()
