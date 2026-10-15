# SPDX-License-Identifier: AGPL-3.0-only
# Official PyInstaller onedir bundle. No user paths or PDF/data globs.
from pathlib import Path
import hashlib
root=Path(SPECPATH)
app=root/'app'
data=[(str(app/'safe_images.json'),'.')]
exclusions=['pytest','pip','setuptools','unittest','tkinter.test','test','matplotlib','numpy','scipy','IPython']

redist=Path('C:/Program Files/Microsoft Visual Studio/18/Community/VC/Redist/MSVC/14.51.36231/x64/Microsoft.VC145.CRT')
expected={'msvcp140.dll':'7c26614e1d733892c2deac7e245ce115504b1d80592dd0a01b08e3e5a55f89ca','vcruntime140.dll':'d1f4225df2cd877dbf130d5668a021dce3f94118455ff5ec952061c30afc9ce7','vcruntime140_1.dll':'a7146c08f89fe5b04541ab507cdb59ff7b44534d4ba3c668a426c6450a03434e'}
def controlled_binaries(rows):
 result=[];seen=set()
 for destination,source,kind in rows:
  leaf=Path(destination).name.lower()
  if leaf=='ucrtbase.dll' or leaf.startswith('api-ms-win-'):continue
  if leaf in expected:
   p=redist/leaf
   assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[leaf]
   source=str(p);seen.add(leaf)
  result.append((destination,source,kind))
 for leaf in expected.keys()-seen:
  p=redist/leaf;assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[leaf]
  result.append((p.name,str(p),'BINARY'))
 return result
gui_a=Analysis([str(app/'release_gui.py')],pathex=[str(app)],datas=data,hiddenimports=[],excludes=exclusions,noarchive=False)
gui_a.binaries=controlled_binaries(gui_a.binaries)
gui=EXE(PYZ(gui_a.pure),gui_a.scripts,[],exclude_binaries=True,name='PDFRedactor',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,version=str(root/'version_info.txt'),uac_admin=False)
worker_a=Analysis([str(app/'release_worker.py')],pathex=[str(app)],datas=data,hiddenimports=[],excludes=exclusions,noarchive=False)
worker_a.binaries=controlled_binaries(worker_a.binaries)
worker=EXE(PYZ(worker_a.pure),worker_a.scripts,[],exclude_binaries=True,name='PDFRedactorWorker',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=True,version=str(root/'version_info.txt'),uac_admin=False)
collect=COLLECT(gui,worker,gui_a.binaries,worker_a.binaries,gui_a.datas,worker_a.datas,strip=False,upx=False,name='PDFRedactor')
