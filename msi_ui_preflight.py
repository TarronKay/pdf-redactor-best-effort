# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only checks for this package's dialog graph, references and bounds.

This is not a full ICE suite or a substitute for authorized visible UI testing.
Never opens an installer session or runs an action/sequence.
"""
import ctypes,json,sys
from pathlib import Path
U=ctypes.c_uint;P=ctypes.POINTER(U);S=ctypes.c_wchar_p
api=ctypes.WinDLL('msi')
def bind(name,args):
 f=getattr(api,name);f.argtypes=args;f.restype=U;return f
op=bind('MsiOpenDatabaseW',[S,ctypes.c_void_p,P]);view=bind('MsiDatabaseOpenViewW',[U,S,P])
execute=bind('MsiViewExecute',[U,U]);fetch=bind('MsiViewFetch',[U,P]);close=bind('MsiCloseHandle',[U]);get=bind('MsiRecordGetStringW',[U,U,S,P])
def check(code):
 if code:raise RuntimeError('Read-only MSI database error '+str(code))
def query(db,sql,count):
 h=U();check(view(db,sql,ctypes.byref(h)));rows=[]
 try:
  check(execute(h,0))
  while True:
   r=U();code=fetch(h,ctypes.byref(r))
   if code==259:break
   check(code)
   try:
    row=[]
    for i in range(1,count+1):
     b=ctypes.create_unicode_buffer(65536);n=U(len(b));check(get(r,i,b,ctypes.byref(n)));row.append(b.value)
    rows.append(row)
   finally:close(r)
 finally:close(h)
 return rows
def validate_rows(dialogs,controls,events):
 errors=[];report=[]
 known={d[0] for d in dialogs}
 for c in controls:
  if c[0] not in known:errors.append('Unknown dialog for '+c[0]+'.'+c[1])
 for d in dialogs:
  name,width,height,first,default,cancel=d;width=int(width);height=int(height)
  rows={c[1]:c for c in controls if c[0]==name}
  edges={c[1]:c[8] for c in rows.values() if c[8]}
  incoming={n:[] for n in edges}
  for source,target in edges.items():
   if target not in edges:errors.append(f'{name}: broken tab edge {source}->{target}')
   else:incoming[target].append(source)
  for target,sources in incoming.items():
   if len(sources)!=1:errors.append(f'{name}: tab predecessor count {len(sources)} for {target}: {sources}')
  visited=[];cursor=first
  while cursor in edges and cursor not in visited:
   visited.append(cursor);cursor=edges[cursor]
  if not visited or cursor!=first or set(visited)!=set(edges):errors.append(name+': tab pointers do not form one closed cycle from first control')
  for key,control in [('first',first),('default',default),('cancel',cancel)]:
   if control and control not in rows:errors.append(f'{name}: invalid {key} reference {control}')
  for control in [default,cancel]:
   if control and control in rows and rows[control][2]!='PushButton':errors.append(name+': default/cancel must reference a push button')
  for c in rows.values():
   _,cid,kind,x,y,w,h,attrs,nxt=c;x,y,w,h,attrs=map(int,[x,y,w,h,attrs])
   if x<0 or y<0 or w<=0 or h<=0 or x+w>width or y+h>height:errors.append(f'{name}.{cid}: control exceeds dialog bounds')
   if cid in edges and kind not in {'ScrollableText','CheckBox','PushButton'}:errors.append(f'{name}.{cid}: unexpected control type in this package tab cycle')
   if cid in edges and attrs&3!=3:errors.append(f'{name}.{cid}: cycle member is not visible/enabled by default')
  report.append(dict(dialog=name,tab_cycle=visited,static_controls_without_tab_edge=sorted(set(rows)-set(edges))))
 for dialog,control,event,arg,condition in events:
  if (dialog,control) not in {(c[0],c[1]) for c in controls}:errors.append('Event references unknown control')
  if event=='EndDialog' and arg not in {'Return','Exit','Retry','Ignore'}:errors.append('Invalid EndDialog argument')
  if not condition:errors.append('Event condition is empty')
 if errors:raise ValueError('; '.join(errors))
 return report
def validate_msi(path):
 h=U();check(op(str(Path(path).resolve()),None,ctypes.byref(h)))
 try:
  dialogs=query(h,'SELECT `Dialog`,`Width`,`Height`,`Control_First`,`Control_Default`,`Control_Cancel` FROM `Dialog`',6)
  controls=query(h,'SELECT `Dialog_`,`Control`,`Type`,`X`,`Y`,`Width`,`Height`,`Attributes`,`Control_Next` FROM `Control`',9)
  events=query(h,'SELECT `Dialog_`,`Control_`,`Event`,`Argument`,`Condition` FROM `ControlEvent`',5)
  return dict(passed=True,dialogs=validate_rows(dialogs,controls,events),read_only_database=True,installer_actions_executed=False,visible_gui_tested=False)
 finally:close(h)
if __name__=='__main__':print(json.dumps(validate_msi(sys.argv[1]),indent=2))
