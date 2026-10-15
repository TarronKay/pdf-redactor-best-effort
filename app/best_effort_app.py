# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Best-effort UI: eligibility/checking advisory, file checks enforced."""
import base64,hashlib
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
from ui_workflow import WorkflowUI
from best_effort_controller import call_best_effort_worker
from preview_cache import cache_key
from review_state import clone
from export_files import write_new_pair

class BestEffortApp(WorkflowUI):
    def __init__(self,root):
        super().__init__(root)
        root.title('PDF Redactor - Best effort')
        head=root.winfo_children()[0]
        head.winfo_children()[0].configure(text='PDF Redactor - Best effort')
        head.winfo_children()[1].configure(text='Local processing. Source document metadata is removed. Page checks are optional; inspect the exported content yourself.')
        for widget in root.winfo_children():
            if isinstance(widget,ttk.Label) and str(widget.cget('text')).startswith('Drag to add a region.'):
                widget.configure(text='Drag to add a box; right-click to remove it. Boxes follow the displayed page orientation. Checking pages is optional.')
        self.buttons[3].configure(text='Next',command=lambda:self.navigate(1))
        self.buttons[5].configure(text='Mark checked (optional)',command=self.mark_reviewed)
        self.buttons[5].pack(side='left',padx=3,before=self.buttons[6])
        choices=[w for w in self.advanced.winfo_children() if isinstance(w,ttk.Radiobutton)]
        if len(choices)==2:
            choices[0].configure(text='Selectable text (best effort)')
            choices[1].configure(text='Image-only (no text layer)')
        self.status.set('Open a PDF, draw redactions, then export. Checking pages is optional; inspect the result yourself.')
        self._set_mode_label();self._update_controls()

    def _mode(self):return 'best-effort-text' if self.selectable.get() else 'best-effort-raster'

    def _set_mode_label(self):
        self.mode_status.set('BEST EFFORT selectable text: hidden/occluded or other identifiers may remain searchable. Check text and pixels.' if self.selectable.get() else 'IMAGE ONLY: no text layer; visible identifiers outside selected boxes can remain. Inspect the output.')

    def _launch_refresh(self):
        self._refresh_job=None
        if self._closed or not self._pending or self.data is None:return
        if self.busy:self._refresh_job=self.root.after(50,self._launch_refresh);return
        generation=self._generation;key=self._analysis_key();data=self.data;options=clone(self.options())
        def operation():
            try:return call_best_effort_worker(data,'analyze',options=options)
            except Exception as error:return {'refresh_error':str(error)}
        self.run(operation,lambda result:self._refresh_done(result,generation,key))

    def _refresh_done(self,result,generation,key):
        if self._closed:return
        if generation!=self._generation or key!=self._analysis_key():
            if self._pending and self._refresh_job is None:self._refresh_job=self.root.after(0,self._launch_refresh)
            return
        if 'refresh_error' in result:self.status.set('File could not be prepared: '+result['refresh_error']);return
        if result.get('sha256')!=key[0]:self.status.set('Source changed; select the PDF again.');return
        regions=[];seen=set()
        # No suggestion update may silently remove an already selected box.
        for r in self.regions+result['regions']:
            identity=(r['page'],tuple(r['rect']))
            if identity not in seen:regions.append(clone(r));seen.add(identity)
        self.info=result;self.regions=regions;self._pending=False
        self.page=min(self.page,len(result['pages'])-1);self.final.set(True)
        self._sync_reviewed();self.show()

    def show(self):
        if not self.info or self.busy or self._pending:return
        data=self.data;options=clone(self.options());regions=clone(self.regions) if self.final.get() else None
        page=self.page;signature=self.signature();mode=self._mode()
        self.preview_signature=None;self._displayed_page_key=None
        if regions is not None:self.preview_error=None
        def operation():
            try:
                if regions is not None:
                    result=self.preview_cache.get(data,regions,options,mode,lambda raw,boxes,policy:call_best_effort_worker(raw,'prepare_previews',regions=boxes,options=policy,mode=mode))
                    return dict(png=result['pages'][page])
                return call_best_effort_worker(data,'preview',page=page,mode=mode)
            except Exception as error:return dict(preview_error=str(error))
        def done(result):
            if signature!=self.signature() or self._pending:return
            if 'preview_error' in result:
                self.preview_error=result['preview_error'];self.preview_signature=None;self._displayed_page_key=None
                self.status.set('Preview unavailable: '+self.preview_error+' Export will still verify the current selected redactions.');return
            self.display(result,signature)
        self.run(operation,done)

    def display(self,result,signature):
        super().display(result,signature)
        if signature!=self.signature() or self._pending:return
        warnings=self.info.get('warnings',[])
        view='Redacted preview' if self.final.get() else 'Original page'
        self.status.set(f'{view} {self.page+1}/{len(self.info["pages"])} | {len(self.regions)} redactions | {len(self.reviewed)} pages checked (optional). Export does not require checking every page. '+('Advisory: '+' '.join(warnings) if warnings else 'Inspect selected boxes and missed identifiers.'))

    def navigate(self,delta):
        if self._pending or self.busy:return
        super().navigate(delta)

    def _can_export(self):
        return bool(not self._closed and self.data is not None and self.info and not self.busy and not self._pending)

    def _update_controls(self):
        super()._update_controls()
        if not hasattr(self,'buttons') or len(self.buttons)<7:return
        ready=bool(self.info and not self.busy and not self._pending)
        self.buttons[3].configure(text='Next' if not self.info or self.page<len(self.info['pages'])-1 else 'Last page',state='normal' if ready and self.page<len(self.info['pages'])-1 else 'disabled')
        self.buttons[5].configure(state='normal' if self._can_review() else 'disabled')
        if hasattr(self,'original_next'):self.original_next.pack_forget()

    def export(self):
        if not self._can_export():self.status.set('Wait for file preparation and pending identifier updates. No page-check requirement applies.');return
        data=self.data;options=clone(self.options());regions=clone(self.regions);mode=self._mode()
        epoch=self._epoch;state=cache_key(data,regions,options,mode);checked=sorted(self.reviewed)
        cached=self.preview_cache.peek(data,regions,options,mode)
        path=filedialog.asksaveasfilename(defaultextension='.pdf',initialfile='redacted-copy.pdf',filetypes=[('PDF','*.pdf')],confirmoverwrite=False)
        if not path:return
        def current():return self._can_export() and epoch==self._epoch and state==cache_key(self.data,self.regions,self.options(),self._mode())
        if not current():self.status.set('Settings changed; export the current redactions again.');return
        def done(result):
            if not current():self.status.set('Settings changed during export; nothing was saved.');return
            try:
                saved=write_new_pair(path,base64.b64decode(result['pdf']),result['report'])
                self.status.set(f'Saved {saved.pdf_path.name} and {saved.report_path.name} in {saved.pdf_path.parent}. Check the result for remaining identifiers.')
            except Exception as error:messagebox.showerror('Export failed',str(error))
        self.run(lambda:call_best_effort_worker(data,'export',regions=regions,options=options,mode=mode,checked=checked,expected_output_sha256=cached['output_sha256'] if cached else None),done)

if __name__=='__main__':
    root=tk.Tk();BestEffortApp(root);root.mainloop()
