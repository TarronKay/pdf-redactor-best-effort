# SPDX-License-Identifier: AGPL-3.0-only
"""Build the isolated regression candidate with explicit runtime search paths."""
from pathlib import Path
import os,subprocess,sys,json
ROOT=Path(__file__).resolve().parent
def main():
 target=(ROOT/'dist/PDFRedactor').resolve()
 assert target.is_relative_to(ROOT.resolve()) and target.name=='PDFRedactor' and not (ROOT/'dist').is_symlink() and not target.is_symlink()
 python=Path(sys.executable).resolve()
 env=os.environ.copy();env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
 env.update(TEMP=str(ROOT/'build-temp'),TMP=str(ROOT/'build-temp'),PIP_NO_INDEX='1',PIPCL_SHOW_ENV='0')
 redist=Path('C:/Program Files/Microsoft Visual Studio/18/Community/VC/Redist/MSVC/14.51.36231/x64/Microsoft.VC145.CRT')
 env['PATH']=os.pathsep.join([str(python.parent),str(redist),str(Path(os.environ['SystemRoot'])/'System32'),str(Path(os.environ['SystemRoot'])),str(Path(sys.base_prefix)),str(Path(sys.base_prefix)/'DLLs')])
 command=[str(python),'-m','PyInstaller','--noconfirm','--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'pyinstaller-work'),str(ROOT/'redactor.spec')]
 with (ROOT/'freeze-build.log').open('w',encoding='utf-8') as log:run=subprocess.run(command,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=600)
 (ROOT/'freeze-build-result.json').write_text(json.dumps(dict(exit_code=run.returncode,command=command,controlled_path=env['PATH'],old_artifacts_modified=False),indent=2))
 print('Frozen candidate build exit',run.returncode);raise SystemExit(run.returncode)
if __name__=='__main__':main()
