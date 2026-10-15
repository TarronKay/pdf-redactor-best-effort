# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
import hashlib, json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui_base import CanvasUI
from preview_cache import PreviewCache, cache_key
from review_state import clone, page_key
from engine import MAX_BYTES

class WorkflowUI(CanvasUI):
    DEBOUNCE_MS = 400

    def __init__(self, root):
        self._init_state()
        self.preview_cache = PreviewCache()
        self.selectable = tk.BooleanVar(root, value=True)
        self.mode_status = tk.StringVar(root, value='')
        self.preview_error = None
        super().__init__(root)
        self.final.set(True)
        self.terms.unbind('<KeyRelease>')
        self.terms.edit_modified(False)
        self.terms.bind('<<Modified>>', self.identifiers_changed)
        self.buttons[1].configure(text='Refresh suggestions')
        self.buttons[6].configure(text='Export redacted copy')
        final = next((w for w in self.controls if isinstance(w, ttk.Checkbutton) and w.cget('text').startswith('Show destructive')))
        final.configure(text='Show redacted page (black boxes)')
        mode_row = ttk.Frame(root, padding=(12, 4))
        mode_row.pack(fill='x', before=root.winfo_children()[1])
        ttk.Label(mode_row, textvariable=self.mode_status).pack(side='left')
        ttk.Button(mode_row, text='Advanced options', command=self.toggle_advanced).pack(side='right')
        self.advanced = ttk.Frame(root, padding=(12, 4))
        self.mode_choice = tk.StringVar(root, value='text')
        for label, value in [('Selectable text (best effort)', 'text'), ('Image-only (no text layer)', 'raster')]:
            choice = ttk.Radiobutton(self.advanced, text=label, variable=self.mode_choice, value=value, command=self.mode_changed)
            choice.pack(side='left', padx=6)
            self.controls.append(choice)
        ttk.Label(root, text='Enter names or IDs; suggestions refresh automatically and ignore letter case. Check for missed identifiers. Drag to add redactions; right-click to remove.', wraplength=1120, padding=(12, 2)).pack(fill='x', before=mode_row)

    def _init_state(self):
        self._epoch = 0
        self._generation = 0
        self._pending = False
        self._refresh_job = None
        self._approvals = {}
        self._displayed_page_key = None
        self._last_terms = ()
        self._closed = False

    def toggle_advanced(self):
        if self.advanced.winfo_manager():
            self.advanced.pack_forget()
        else:
            self.advanced.pack(fill='x', after=self.buttons[0].master)

    def _page_key(self, page):
        return page_key(self.data, page, self.regions, self.options(), self._mode())

    def _sync_reviewed(self):
        count = len(self.info['pages']) if self.info else 0
        for p, key in list(self._approvals.items()):
            if self.data is None or p < 0 or p >= count or (key != self._page_key(p)):
                del self._approvals[p]
        self.reviewed = set(self._approvals)

    def signature(self):
        return super().signature() + (self._epoch,)

    def invalidate(self):
        self._epoch += 1
        self.preview_cache.clear()
        self.preview_signature = None
        self._displayed_page_key = None
        self._sync_reviewed()
        self._update_controls()

    def identifiers_changed(self, event=None):
        if event is not None and (not self.terms.edit_modified()):
            return
        if event is not None:
            self.terms.edit_modified(False)
        terms = tuple(self.options()['terms'])
        if terms != self._last_terms:
            self._last_terms = terms
            self.request_refresh()

    def policy_changed(self):
        self.request_refresh()

    def mode_changed(self):
        self.selectable.set(self.mode_choice.get() == 'text')
        self._set_mode_label()
        self.request_refresh()

    def suggest(self):
        self.request_refresh(delay=0)

    def request_refresh(self, delay=None):
        self._generation += 1
        self._pending = self.data is not None
        self.invalidate()
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
            self._refresh_job = None
        if self._pending:
            self.status.set('Updating identifier suggestions. Review and export are paused; manual redactions are kept.')
            self._refresh_job = self.root.after(self.DEBOUNCE_MS if delay is None else delay, self._launch_refresh)
        self._update_controls()

    def _analysis_key(self):
        return (hashlib.sha256(self.data).hexdigest() if self.data is not None else None, self._mode(), json.dumps(self.options(), sort_keys=True))

    def select(self):
        path = filedialog.askopenfilename(filetypes=[('PDF', '*.pdf')])
        if not path:
            return
        try:
            with open(path, 'rb') as file:
                data = file.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('PDF exceeds 20 MiB.')
            self.data = data
            self.info = None
            self.page = 0
            self.regions = []
            self._approvals.clear()
            self.reviewed.clear()
            self.preview_error = None
            self.final.set(True)
            self.request_refresh(delay=0)
        except Exception as error:
            messagebox.showerror('Cannot open PDF', str(error))

    def run(self, operation, success):
        epoch = self._epoch

        def guarded():
            try:
                return {'result': operation()}
            except Exception as error:
                return {'task_error': str(error)}

        def completed(envelope):
            if self._closed:
                return
            if 'task_error' in envelope:
                if epoch == self._epoch:
                    self.status.set('Processing stopped: ' + envelope['task_error'])
            else:
                success(envelope['result'])
            self._update_controls()
        super().run(guarded, completed)
        if not self._closed:
            self.terms.configure(state='normal')
            self._update_controls()

    def _can_review(self):
        return bool(not self._closed and self.data is not None and self.info and (not self.busy) and (not self._pending) and (not self.info['blockers']) and (not self.preview_error) and self.final.get() and (self.preview_signature == self.signature()) and (self._displayed_page_key == self._page_key(self.page)))

    def mark_reviewed(self):
        if not self._can_review():
            self.status.set('Wait for current suggestions and a successful redacted-page preview before marking reviewed.')
            return False
        self._approvals[self.page] = self._page_key(self.page)
        self._sync_reviewed()
        self._update_controls()
        return True

    def mark_and_next(self):
        if not self.mark_reviewed():
            return
        count = len(self.info['pages'])
        if self.page < count - 1:
            self.page += 1
            self.show()
        elif len(self.reviewed) == count:
            self.status.set(f'All {count} pages reviewed. Export redacted copy is ready.')
        else:
            self.status.set(f'Last page reviewed; {len(self.reviewed)}/{count} complete. Use Previous to review the remaining pages.')

    def _update_controls(self):
        if not hasattr(self, 'buttons') or len(self.buttons) < 7:
            return
        locked = self.busy or self._pending
        for i, button in enumerate(self.buttons):
            button.configure(state='disabled' if locked or (i >= 2 and (not self.info)) else 'normal')
        if not self.busy:
            self.buttons[0].configure(state='normal')
            self.buttons[1].configure(state='normal' if self.data is not None else 'disabled')
        self.buttons[3].configure(text='Mark last page reviewed' if self.info and self.page == len(self.info['pages']) - 1 else 'Mark reviewed and go next', state='normal' if self._can_review() else 'disabled')
        self.buttons[6].configure(state='normal' if self._can_export() else 'disabled')
        if hasattr(self, 'original_next'):
            if self.info and (not self.final.get()):
                self.original_next.pack(side='left', padx=3, before=self.buttons[4])
            else:
                self.original_next.pack_forget()
            self.original_next.configure(state='normal' if self.info and (not locked) and (self.page < len(self.info['pages']) - 1) else 'disabled')

    def close(self):
        self._closed = True
        self._generation += 1
        if self._refresh_job is not None:
            self.root.after_cancel(self._refresh_job)
        self.preview_cache.clear()
        super().close()

    def display(self, result, signature):
        if self._pending or signature != self.signature():
            return
        super().display(result, signature)
        if self.final.get() and (not self.preview_error) and (not self.info['blockers']):
            self._displayed_page_key = self._page_key(self.page)
            self.status.set(f"Page {self.page + 1}/{len(self.info['pages'])} | {len(self.reviewed)} reviewed. Check all black boxes and any missed identifiers, then mark reviewed.")
        else:
            self._displayed_page_key = None
            reason = self.preview_error or ' '.join(self.info['blockers'])
            self.status.set('Original page shown; it cannot be marked reviewed. ' + (reason or 'Turn on Show redacted page to review.'))
        self._update_controls()

    def navigate(self, delta):
        if self._pending:
            return
        super().navigate(delta)
        self._update_controls()
