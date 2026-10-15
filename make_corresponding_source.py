# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit source closure; no build output, owner documents or recursive ZIP."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent
ROOT_FILES=['README.md','LICENSE','LICENSING.md','README.txt','SOURCE-INFO.txt','BUILDING.md','build_frozen.py','build_msi.py','prepare_notices.py','redactor.spec','version_info.txt','msi_ui_preflight.py','test_ui_preflight.py','requirements-runtime-build.txt','requirements-test.txt','requirements-native-tools.txt','pytest.ini','make_corresponding_source.py','licensed-source-manifest.json']
def main():
 files=[ROOT/name for name in ROOT_FILES]
 for folder in ['app','tests','notices','source-provenance','upstream']:
  files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
 names=sorted(set(p.relative_to(ROOT).as_posix() for p in files));rows=[]
 for name in names:
  p=ROOT/name
  assert p.is_file() and not p.is_symlink() and '..' not in Path(name).parts
  rows.append(dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 (ROOT/'source-file-manifest.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
 output=ROOT/'corresponding-source/PDFRedactor-0.9.2-CORRESPONDING-SOURCE.zip';output.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(output,'x',allowZip64=True) as z:
  for row in rows:z.write(ROOT/row['path'],row['path'],compress_type=zipfile.ZIP_STORED if row['path'].endswith(('.tar.gz','.tar.xz')) else zipfile.ZIP_DEFLATED)
  z.write(ROOT/'source-file-manifest.json','source-file-manifest.json',compress_type=zipfile.ZIP_DEFLATED)
 print(json.dumps(dict(file=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),entries=len(rows)+1)))
if __name__=='__main__':main()
