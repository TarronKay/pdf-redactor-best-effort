# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
import hashlib
class Var:
    def __init__(self, master=None, value=None): self.value=value; self.traces=[]
    def get(self): return self.value
    def set(self, value):
        self.value=value
        for callback in self.traces: callback('var','','write')
    def trace_add(self, mode, callback): self.traces.append(callback)

class Widget:
    def __init__(self, master=None, **settings):
        self.master=master; self.settings=settings; self.children=[]; self.manager=''; self.bindings={}
        if master is not None: master.children.append(self)
    def configure(self, **settings): self.settings.update(settings)
    def cget(self, key): return self.settings.get(key,'')
    def pack(self, **settings): self.manager='pack'
    def pack_forget(self): self.manager=''
    def winfo_manager(self): return self.manager
    def winfo_children(self): return list(self.children)
    def winfo_width(self): return 1160
    def bind(self, event, callback): self.bindings[event]=callback
    def unbind(self, event): self.bindings.pop(event,None)
    def invoke(self):
        if self.settings.get('state')!='disabled': return self.settings.get('command',lambda:None)()
    def set(self, *args): pass
    def yview(self, *args): pass
    def yview_moveto(self, *args): pass
    def delete(self, *args): pass

class Frame(Widget): pass

class Label(Widget): pass

class Button(Widget): pass

class Checkbutton(Widget): pass

class Radiobutton(Widget): pass

class Scrollbar(Widget): pass

class Canvas(Widget): pass

class Text(Widget):
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs); self.value=''; self.modified=False
    def get(self,*args): return self.value
    def edit_modified(self,value=None):
        if value is not None: self.modified=value
        return self.modified

class Root(Widget):
    def __init__(self): super().__init__(); self.manager='root'; self.jobs={}; self.serial=0
    def title(self, value): self.window_title=value
    def geometry(self, value): self.window_geometry=value
    def protocol(self,*args): pass
    def after(self,delay,callback):
        self.serial+=1;self.jobs[self.serial]=(delay,callback);return self.serial
    def after_cancel(self,key): self.jobs.pop(key,None)
    def destroy(self): self.destroyed=True

def load(ui, count=2):
    ui.data=b'independent-source'
    ui.info=dict(sha256=hashlib.sha256(ui.data).hexdigest(), pages=[dict(width=612,height=792) for i in range(count)],regions=[],blockers=[],category='test')
    ui._update_controls()

def finish(ui):
    # Actual App.run thread enqueues its real completion; no Tk event loop.
    callback=ui.completions.get(timeout=5);callback()

def visible(widget):
    return bool(widget.winfo_manager()) and (widget.master is None or visible(widget.master))
