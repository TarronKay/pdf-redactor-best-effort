# SPDX-License-Identifier: AGPL-3.0-only
"""Single per-user MSI, using signed Windows makecab and documented MSI APIs.

No services, custom executable actions, shell execution, privilege elevation,
wildcard deletion, downloaded installer-builder, or real report files.
"""
import ctypes,hashlib,json,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PRODUCT='{44B284EC-9164-472F-BD86-AB02E1C3B6A1}'
UPGRADE='{74DA9196-0875-436F-A680-89A084BBE538}'
NS=uuid.UUID(UPGRADE.strip('{}'))
msi=ctypes.WinDLL('msi',use_last_error=True)
U=ctypes.c_uint;P=ctypes.POINTER(U);S=ctypes.c_wchar_p
def setup(name,args,restype=U):
 f=getattr(msi,name);f.argtypes=args;f.restype=restype;return f
opendb=setup('MsiOpenDatabaseW',[S,ctypes.c_void_p,P])
viewopen=setup('MsiDatabaseOpenViewW',[U,S,P]);execute=setup('MsiViewExecute',[U,U]);close=setup('MsiCloseHandle',[U]);commit=setup('MsiDatabaseCommit',[U])
record=setup('MsiCreateRecord',[U]);setstr=setup('MsiRecordSetStringW',[U,U,S]);setint=setup('MsiRecordSetInteger',[U,U,ctypes.c_int]);setstream=setup('MsiRecordSetStreamW',[U,U,S])
sumopen=setup('MsiGetSummaryInformationW',[U,S,U,P]);sumset=setup('MsiSummaryInfoSetPropertyW',[U,U,U,ctypes.c_int,ctypes.c_void_p,S]);sumpersist=setup('MsiSummaryInfoPersist',[U])
def check(code,action):
 if code:raise RuntimeError(f'{action}: Windows Installer error {code}')
class DB:
 def __init__(self,path):self.columns={};self.h=U();check(opendb(str(path),ctypes.c_void_p(3),ctypes.byref(self.h)),'create MSI')
 def sql(self,sql,values=(),stream_index=None):
  view=U();check(viewopen(self.h,sql,ctypes.byref(view)),sql)
  rec=record(len(values)) if values else 0
  try:
   for i,value in enumerate(values,1):
    if value is None:continue
    check(setstream(rec,i,str(value)) if i==stream_index else setint(rec,i,value) if isinstance(value,int) else setstr(rec,i,str(value)),'set field')
   check(execute(view,rec),'execute '+sql)
  finally:
   if rec:close(rec)
   close(view)
 def table(self,name,columns,keys):
  self.columns[name]=[n for n,t in columns]
  self.sql('CREATE TABLE `'+name+'` ('+', '.join('`'+n+'` '+t for n,t in columns)+' PRIMARY KEY '+', '.join('`'+k+'`' for k in keys)+')')
 def insert(self,name,values):self.sql('INSERT INTO `'+name+'` ('+','.join('`'+c+'`' for c in self.columns[name])+') VALUES ('+','.join('?' for _ in values)+')',values)
def ident(prefix,path):return prefix+hashlib.sha256(str(path).encode()).hexdigest()[:20]

def rtf(text):
 result=[]
 for char in text:
  n=ord(char)
  if char in '\\{}':result.append('\\'+char)
  elif char=='\n':result.append('\\par\n')
  elif char=='\r':continue
  elif n>127:result.append('\\u'+str(n if n<32768 else n-65536)+'?')
  else:result.append(char)
 return '{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Segoe UI;}}\\f0\\fs16 '+''.join(result)+'}'
def main():
 payload=ROOT/'dist/PDFRedactor';output=ROOT/'artifacts';output.mkdir(exist_ok=True)
 for name in ['README.txt','LICENSE','LICENSING.md','SOURCE-INFO.txt']:
  import shutil
  shutil.copyfile(ROOT/name,payload/name)
 # All root files are explicit. Everything beneath _internal is audited output
 # from the fixed PyInstaller spec, never copied from the prototype workspace.
 allowed_root={'PDFRedactor.exe','PDFRedactorWorker.exe','README.txt','LICENSE','LICENSING.md','SOURCE-INFO.txt'}
 files=sorted(p for p in payload.rglob('*') if p.is_file())
 for p in files:
  relative=p.relative_to(payload)
  if relative.parts[0] not in {'_internal','ThirdPartyNotices'} and str(relative) not in allowed_root:raise RuntimeError('Unexpected release root file: '+str(relative))
  if p.suffix.lower() in {'.pdf','.jsonl','.pem','.key','.pfx','.p12'}:raise RuntimeError('Forbidden payload extension: '+str(relative))
  if any(part.lower() in {'output','samples','tests','tmp','experiments','.git','library-transfer','exact-failing-inputs'} for part in relative.parts):raise RuntimeError('Forbidden release directory')
 manifest=[dict(path=p.relative_to(payload).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
 (ROOT/'payload-manifest.json').write_text(json.dumps(manifest,indent=2))
 cabdir=ROOT/'cab-build';cabdir.mkdir(exist_ok=True)
 cabinet='payload-'+uuid.uuid4().hex[:10]+'.cab'
 ddf=['.OPTION EXPLICIT','.Set Cabinet=ON','.Set Compress=ON','.Set CompressionType=MSZIP','.Set MaxDiskSize=0',f'.Set CabinetNameTemplate={cabinet}',f'.Set DiskDirectoryTemplate={cabdir}']
 ddf.extend(f'"{p}" F{i:06d}' for i,p in enumerate(files,1))
 ddffile=cabdir/'payload.ddf';ddffile.write_text('\n'.join(ddf),encoding='utf-8')
 print('Building cabinet for '+str(len(files))+' allowlisted payload files.',flush=True)
 subprocess.run([r'C:\Windows\System32\makecab.exe','/F',str(ddffile)],cwd=cabdir,check=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL)
 path=output/'PDFRedactor-BestEffort-0.9.2-x64-EVALUATION.msi'
 if path.exists():raise RuntimeError('Refusing to replace an existing MSI; choose a fresh build output directory.')
 db=DB(path);print('Creating MSI tables.',flush=True)
 schemas={
 'Property':([('Property','CHAR(72) NOT NULL'),('Value','CHAR(0) NOT NULL LOCALIZABLE')],['Property']),
 'Directory':([('Directory','CHAR(72) NOT NULL'),('Directory_Parent','CHAR(72)'),('DefaultDir','CHAR(255) NOT NULL LOCALIZABLE')],['Directory']),
 'Component':([('Component','CHAR(72) NOT NULL'),('ComponentId','CHAR(38)'),('Directory_','CHAR(72) NOT NULL'),('Attributes','SHORT NOT NULL'),('Condition','CHAR(255)'),('KeyPath','CHAR(72)')],['Component']),
 'Feature':([('Feature','CHAR(38) NOT NULL'),('Feature_Parent','CHAR(38)'),('Title','CHAR(64) LOCALIZABLE'),('Description','CHAR(255) LOCALIZABLE'),('Display','SHORT'),('Level','SHORT NOT NULL'),('Directory_','CHAR(72)'),('Attributes','SHORT NOT NULL')],['Feature']),
 'FeatureComponents':([('Feature_','CHAR(38) NOT NULL'),('Component_','CHAR(72) NOT NULL')],['Feature_','Component_']),
 'File':([('File','CHAR(72) NOT NULL'),('Component_','CHAR(72) NOT NULL'),('FileName','CHAR(255) NOT NULL LOCALIZABLE'),('FileSize','LONG NOT NULL'),('Version','CHAR(72)'),('Language','CHAR(20)'),('Attributes','SHORT'),('Sequence','LONG NOT NULL')],['File']),
 'Media':([('DiskId','SHORT NOT NULL'),('LastSequence','LONG NOT NULL'),('DiskPrompt','CHAR(64) LOCALIZABLE'),('Cabinet','CHAR(255)'),('VolumeLabel','CHAR(32)'),('Source','CHAR(72)')],['DiskId']),
 'Shortcut':([('Shortcut','CHAR(72) NOT NULL'),('Directory_','CHAR(72) NOT NULL'),('Name','CHAR(128) NOT NULL LOCALIZABLE'),('Component_','CHAR(72) NOT NULL'),('Target','CHAR(72) NOT NULL'),('Arguments','CHAR(255)'),('Description','CHAR(255) LOCALIZABLE'),('Hotkey','SHORT'),('Icon_','CHAR(72)'),('IconIndex','SHORT'),('ShowCmd','SHORT'),('WkDir','CHAR(72)')],['Shortcut']),
 'InstallExecuteSequence':([('Action','CHAR(72) NOT NULL'),('Condition','CHAR(255)'),('Sequence','SHORT')],['Action']),
 'InstallUISequence':([('Action','CHAR(72) NOT NULL'),('Condition','CHAR(255)'),('Sequence','SHORT')],['Action']),
 'LaunchCondition':([('Condition','CHAR(255) NOT NULL'),('Description','CHAR(255) NOT NULL LOCALIZABLE')],['Condition']),
 'Registry':([('Registry','CHAR(72) NOT NULL'),('Root','SHORT NOT NULL'),('Key','CHAR(255) NOT NULL LOCALIZABLE'),('Name','CHAR(255) LOCALIZABLE'),('Value','CHAR(0) LOCALIZABLE'),('Component_','CHAR(72) NOT NULL')],['Registry']),
 'RegLocator':([('Signature_','CHAR(72) NOT NULL'),('Root','SHORT NOT NULL'),('Key','CHAR(255) NOT NULL'),('Name','CHAR(255)'),('Type','SHORT')],['Signature_']),
 'AppSearch':([('Property','CHAR(72) NOT NULL'),('Signature_','CHAR(72) NOT NULL')],['Property','Signature_']),
 'Signature':([('Signature','CHAR(72) NOT NULL'),('FileName','CHAR(255) NOT NULL'),('MinVersion','CHAR(20)'),('MaxVersion','CHAR(20)'),('MinSize','LONG'),('MaxSize','LONG'),('MinDate','LONG'),('MaxDate','LONG'),('Languages','CHAR(255)')],['Signature']),
 'Dialog':([('Dialog','CHAR(72) NOT NULL'),('HCentering','SHORT NOT NULL'),('VCentering','SHORT NOT NULL'),('Width','SHORT NOT NULL'),('Height','SHORT NOT NULL'),('Attributes','LONG NOT NULL'),('Title','CHAR(128) LOCALIZABLE'),('Control_First','CHAR(50)'),('Control_Default','CHAR(50)'),('Control_Cancel','CHAR(50)')],['Dialog']),
 'Control':([('Dialog_','CHAR(72) NOT NULL'),('Control','CHAR(50) NOT NULL'),('Type','CHAR(20) NOT NULL'),('X','SHORT NOT NULL'),('Y','SHORT NOT NULL'),('Width','SHORT NOT NULL'),('Height','SHORT NOT NULL'),('Attributes','LONG'),('Property','CHAR(50)'),('Text','CHAR(0) LOCALIZABLE'),('Control_Next','CHAR(50)'),('Help','CHAR(50) LOCALIZABLE')],['Dialog_','Control']),
 'ControlEvent':([('Dialog_','CHAR(72) NOT NULL'),('Control_','CHAR(50) NOT NULL'),('Event','CHAR(50) NOT NULL'),('Argument','CHAR(255) NOT NULL'),('Condition','CHAR(255)'),('Ordering','SHORT')],['Dialog_','Control_','Event','Argument','Condition']),
 'TextStyle':([('TextStyle','CHAR(72) NOT NULL'),('FaceName','CHAR(32) NOT NULL'),('Size','SHORT NOT NULL'),('Color','LONG'),('StyleBits','SHORT')],['TextStyle']),
 'CheckBox':([('Property','CHAR(72) NOT NULL'),('Value','CHAR(64) NOT NULL')],['Property']),
 'ControlCondition':([('Dialog_','CHAR(72) NOT NULL'),('Control_','CHAR(50) NOT NULL'),('Action','CHAR(50) NOT NULL'),('Condition','CHAR(255) NOT NULL')],['Dialog_','Control_','Action'])}
 for name,(cols,keys) in schemas.items():db.table(name,cols,keys)
 properties=dict(ProductCode=PRODUCT,UpgradeCode=UPGRADE,ProductName='PDF Redactor Best Effort - Evaluation',ProductVersion='0.9.2',ProductLanguage='1033',Manufacturer='PDF Redactor AGPL Evaluation',ARPCOMMENTS='Offline best-effort redaction. Unsigned evaluation; inspect every export.',ARPNOMODIFY='1',DefaultUIFont='Normal',MSIFASTINSTALL='0')
 for k,v in properties.items():db.insert('Property',(k,v))
 db.insert('Property',('SecureCustomProperties','MSRUNTIME_ACCEPTED'))
 # Standard read-only registry search avoids VersionNT's compatibility value.
 # REG_SZ CurrentBuildNumber, raw value + 64-bit registry view (2 | 16).
 db.insert('RegLocator',('SupportedWindowsBuild',2,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion','CurrentBuildNumber',18))
 db.insert('AppSearch',('SUPPORTED_OS_BUILD','SupportedWindowsBuild'))
 for row in [('TARGETDIR',None,'SourceDir'),('LocalAppDataFolder','TARGETDIR','.'),('ProgramsDir','LocalAppDataFolder','Programs'),('INSTALLDIR','ProgramsDir','PDFRedactorBestEffort092'),('ProgramMenuFolder','TARGETDIR','.')]:db.insert('Directory',row)
 dirs={Path('.'):'INSTALLDIR'}
 for p in files:
  rel=p.relative_to(payload).parent
  for folder in reversed([rel]+list(rel.parents)):
   if folder in dirs:continue
   did=ident('D',folder);dirs[folder]=did
   db.insert('Directory',(did,dirs[folder.parent],did[:8]+'|'+folder.name))
 db.insert('Feature',('Main',None,'PDF Redactor','Offline PDF redactor',1,1,'INSTALLDIR',0))
 for i,p in enumerate(files,1):
  rel=p.relative_to(payload);fid=f'F{i:06d}';cid=ident('C',rel)
  db.insert('Component',(cid,'{'+str(uuid.uuid5(NS,rel.as_posix())).upper()+'}',dirs[rel.parent],256,None,fid))
  db.insert('FeatureComponents',('Main',cid))
  db.insert('File',(fid,cid,fid+'|'+p.name,p.stat().st_size,None,None,512,i))
  if rel.as_posix()=='PDFRedactor.exe':
   # Non-advertised shortcut anchored by the actual executable component.
   db.insert('Shortcut',('AppShortcut','ProgramMenuFolder','PDF Redactor Best Effort 0.9.2',cid,'[INSTALLDIR]PDFRedactor.exe',None,'Offline PDF redactor - evaluation build',None,None,None,1,'INSTALLDIR'))
 db.insert('Media',(1,len(files),None,'#payload.cab',None,None))
 db.sql('INSERT INTO `_Streams` (`Name`,`Data`) VALUES (?,?)',('payload.cab',cabdir/cabinet),stream_index=2)
 for condition,description in [('Installed OR (VersionNT64 AND SUPPORTED_OS_BUILD >= 10240)','This build requires 64-bit Windows 10 or 11.'),('NOT ALLUSERS','This installer supports current-user installation only. Do not request an all-users install.'),('Installed OR MSRUNTIME_ACCEPTED = "1"','The Microsoft runtime component terms require explicit acceptance. Run interactive setup to review them. This condition applies only to the Microsoft DLLs, not the AGPL application code.')]:db.insert('LaunchCondition',(condition,description))
 sequence=[('LaunchConditions',100),('ValidateProductID',700),('CostInitialize',800),('FileCost',900),('CostFinalize',1000),('InstallValidate',1400),('InstallInitialize',1500),('ProcessComponents',1600),('UnpublishFeatures',1800),('RemoveRegistryValues',2600),('RemoveShortcuts',3200),('RemoveFiles',3500),('InstallFiles',4000),('CreateShortcuts',4500),('WriteRegistryValues',5000),('RegisterUser',6000),('RegisterProduct',6100),('PublishFeatures',6300),('PublishProduct',6400),('InstallFinalize',6600)]
 for action,n in sequence:db.insert('InstallExecuteSequence',(action,None,n))
 db.insert('InstallExecuteSequence',('AppSearch',None,50))
 db.insert('TextStyle',('Normal','Segoe UI',9,None,0))
 terms=(ROOT/'notices/Microsoft/Microsoft-VC-V14-2026-License.txt').read_text(encoding='utf-8')
 db.insert('CheckBox',('MSRUNTIME_ACCEPTED','1'))
 db.insert('Dialog',('WelcomeDlg',50,50,420,360,3,'PDF Redactor 0.9.2 - evaluation','Terms','Continue','Cancel'))
 intro='Original app: GNU AGPL version 3; your source/modification/redistribution rights remain intact. The separate terms below apply only to the three Microsoft runtime DLLs. Setup installs for the current user; no reports are included.'
 db.insert('Control',('WelcomeDlg','Body','Text',20,12,380,47,3,None,intro,None,None))
 db.insert('Control',('WelcomeDlg','Terms','ScrollableText',20,65,380,215,3,None,rtf(terms),'Accept',None))
 db.insert('Control',('WelcomeDlg','Accept','CheckBox',20,288,380,22,3,'MSRUNTIME_ACCEPTED','I accept these terms for the Microsoft runtime components only.','Continue',None))
 db.insert('Control',('WelcomeDlg','Continue','PushButton',330,328,70,20,3,None,'Install','Cancel',None))
 db.insert('Control',('WelcomeDlg','Cancel','PushButton',250,328,70,20,3,None,'Cancel','Terms',None))
 db.insert('ControlCondition',('WelcomeDlg','Continue','Enable','MSRUNTIME_ACCEPTED = "1"'))
 db.insert('ControlCondition',('WelcomeDlg','Continue','Disable','MSRUNTIME_ACCEPTED <> "1"'))
 db.insert('ControlEvent',('WelcomeDlg','Continue','EndDialog','Return','MSRUNTIME_ACCEPTED = "1"',1))
 db.insert('ControlEvent',('WelcomeDlg','Cancel','EndDialog','Exit','1',1))
 db.insert('Dialog',('FinishedDlg',50,50,370,220,3,'Setup complete','Continue','Continue','Continue'))
 db.insert('Control',('FinishedDlg','Body','Text',20,20,330,130,3,None,'PDF Redactor 0.9.2 is available from the Start Menu. Read README, LICENSE, SOURCE-INFO and ThirdPartyNotices. This is an unsigned evaluation candidate; inspect all exports.',None,None))
 db.insert('Control',('FinishedDlg','Continue','PushButton',280,180,70,20,3,None,'Finish','Continue',None))
 db.insert('ControlEvent',('FinishedDlg','Continue','EndDialog','Return','1',1))
 # Component acceptance is checked in execute sequence before any installation.
 # UI must present the terms before LaunchConditions can require acceptance.
 for action,condition,n in [('AppSearch',None,50),('CostInitialize',None,800),('FileCost',None,900),('CostFinalize',None,1000),('WelcomeDlg','NOT Installed',1230),('ExecuteAction',None,1300),('FinishedDlg','NOT REMOVE',-1)]:db.insert('InstallUISequence',(action,condition,n))
 summary=U();check(sumopen(db.h,None,20,ctypes.byref(summary)),'summary')
 for pid,value in [(2,'PDF Redactor Best Effort 0.9.2 Evaluation'),(3,'Per-user offline PDF redactor'),(4,'PDF Redactor AGPL Evaluation'),(7,'x64;1033'),(9,'{'+str(uuid.uuid4()).upper()+'}'),(18,'Native Windows Installer APIs')]:check(sumset(summary,pid,30,0,None,value),'summary string')
 for pid,value in [(14,500),(15,10),(19,2)]:check(sumset(summary,pid,3,value,None,None),'summary int')
 check(sumpersist(summary),'summary persist');close(summary);check(commit(db.h),'commit');close(db.h)
 from msi_ui_preflight import validate_msi
 validation=validate_msi(path)
 print(json.dumps(dict(ui_preflight=validation,installer=str(path),files=len(files),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),product_code=PRODUCT)))
if __name__=='__main__':main()
