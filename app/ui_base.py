# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
import base64, io, queue, threading, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from engine import MAX_BYTES

class CanvasUI(object):

    def __init__(self, root):
        self.root = root
        root.title('PDF Redactor Best Effort')
        root.geometry('1160x900')
        self.data = None
        self.info = None
        self.regions = []
        self.page = 0
        self.reviewed = set()
        self.busy = False
        self.preview_signature = None
        self.institution = tk.BooleanVar(value=True)
        self.dates = tk.BooleanVar(value=True)
        self.final = tk.BooleanVar(value=False)
        head = ttk.Frame(root, padding=12)
        head.pack(fill='x')
        ttk.Label(head, text='PDF Redactor Best Effort', font=('Segoe UI', 19, 'bold')).pack(anchor='w')
        ttk.Label(head, text='Local processing. Suggestions need human review; inspect every export.').pack(anchor='w')
        tools = ttk.Frame(root, padding=(12, 0))
        tools.pack(fill='x')
        self.buttons = []

        def button(label, command):
            b = ttk.Button(tools, text=label, command=command)
            b.pack(side='left', padx=3)
            self.buttons.append(b)
        button('Select PDF', self.select)
        button('Suggest again', self.suggest)
        button('Previous', lambda: self.navigate(-1))
        button('Next', lambda: self.navigate(1))
        button('Clear page regions', self.clear_page)
        button('Mark page reviewed', self.mark_reviewed)
        button('Export separate copy', self.export)
        policy = ttk.Frame(root, padding=12)
        policy.pack(fill='x')
        ttk.Checkbutton(policy, text='Remove institution', variable=self.institution, command=self.policy_changed).pack(side='left')
        ttk.Checkbutton(policy, text='Remove test dates', variable=self.dates, command=self.policy_changed).pack(side='left', padx=12)
        ttk.Checkbutton(policy, text='Show destructive-redaction preview', variable=self.final, command=self.show).pack(side='left')
        ttk.Label(policy, text='Known identifiers (one per line):').pack(side='left', padx=12)
        self.terms = tk.Text(policy, width=27, height=3)
        self.terms.pack(side='left')
        self.terms.bind('<KeyRelease>', lambda e: self.invalidate())
        self.controls = [w for w in policy.winfo_children() if isinstance(w, ttk.Checkbutton)] + [self.terms]
        self.status = tk.StringVar(value='Select a PDF to begin. No real student reports are sent anywhere.')
        ttk.Label(root, textvariable=self.status, wraplength=1120, padding=12).pack(fill='x')
        area = ttk.Frame(root)
        area.pack(fill='both', expand=True, padx=12, pady=4)
        self.canvas = tk.Canvas(area, bg='#dce3ea', highlightthickness=0)
        v = ttk.Scrollbar(area, orient='vertical', command=self.canvas.yview)
        v.pack(side='right', fill='y')
        self.canvas.configure(yscrollcommand=v.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<ButtonPress-1>', self.start)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.end)
        self.canvas.bind('<Button-3>', self.remove)
        ttk.Label(root, text='Drag to add a region. Right-click a region to remove; redraw to adjust. Coordinates use unrotated pages. Re-review after any change.', padding=12).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.completions = queue.SimpleQueue()
        root.after(50, self.poll_completions)

    def poll_completions(self):
        while not self.completions.empty():
            self.completions.get()()
        self.root.after(50, self.poll_completions)

    def options(self):
        return dict(institution=self.institution.get(), dates=self.dates.get(), terms=[s.strip() for s in self.terms.get('1.0', 'end').splitlines() if s.strip()])

    def signature(self):
        return (self.info['sha256'] if self.info else None, self.page, repr(self.regions), repr(self.options()), self.final.get())

    def run(self, operation, success):
        if self.busy:
            return
        self.busy = True
        for b in self.buttons:
            b.configure(state='disabled')
        for w in self.controls:
            w.configure(state='disabled')
        self.status.set('Processing locally in a bounded worker...')

        def task():
            try:
                result = operation()
                error = None
            except Exception as exc:
                result = None
                error = str(exc)

            def done():
                self.busy = False
                for b in self.buttons:
                    b.configure(state='normal')
                for w in self.controls:
                    w.configure(state='normal')
                if error:
                    self.status.set(error)
                    messagebox.showerror('Processing stopped', error)
                else:
                    success(result)
            self.completions.put(done)
        threading.Thread(target=task, daemon=True).start()

    def display(self, result, signature):
        if signature != self.signature():
            self.status.set('Preview changed; render it again before review.')
            return
        im = Image.open(io.BytesIO(base64.b64decode(result['png'])))
        self.scale = min(1.25, max(0.3, (self.canvas.winfo_width() - 30) / im.width))
        im = im.resize((round(im.width * self.scale), round(im.height * self.scale)))
        self.photo = ImageTk.PhotoImage(im)
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, im.width, im.height))
        self.canvas.yview_moveto(0)
        for r in self.regions:
            if r['page'] == self.page:
                self.canvas.create_rectangle(*[v * self.scale for v in r['rect']], outline='#e64b35', width=2, fill='' if self.final.get() else '#f05b40', stipple='' if self.final.get() else 'gray25')
        blockers = ' '.join(self.info['blockers'])
        self.status.set(f"{self.info['category']} | Page {self.page + 1}/{len(self.info['pages'])} | {len(self.regions)} regions | {len(self.reviewed)} pages reviewed. " + (f'EXPORT BLOCKED: {blockers}' if blockers else 'Review every page and check outlined/vector codes manually.'))
        self.preview_signature = signature

    def navigate(self, delta):
        if self.info and (not self.busy):
            self.page = max(0, min(len(self.info['pages']) - 1, self.page + delta))
            self.show()

    def clear_page(self):
        if not self.info or self.busy:
            return
        self.regions = [r for r in self.regions if r['page'] != self.page]
        self.invalidate()
        self.show()

    def point(self, e):
        p = self.info['pages'][self.page]
        return (max(0, min(p['width'], self.canvas.canvasx(e.x) / self.scale)), max(0, min(p['height'], self.canvas.canvasy(e.y) / self.scale)))

    def start(self, e):
        if self.info and (not self.busy):
            self.origin = self.point(e)
            self.drag_id = None

    def drag(self, e):
        if not self.info or self.busy or (not hasattr(self, 'origin')):
            return
        if self.drag_id:
            self.canvas.delete(self.drag_id)
        self.drag_id = self.canvas.create_rectangle(*[v * self.scale for v in (*self.origin, *self.point(e))], outline='#1976d2', width=2)

    def end(self, e):
        if not self.info or self.busy or (not hasattr(self, 'origin')):
            return
        a, b = (self.origin, self.point(e))
        del self.origin
        rect = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        if rect[2] - rect[0] > 2 and rect[3] - rect[1] > 2:
            self.regions.append(dict(page=self.page, rect=rect, reason='manual'))
            self.invalidate()
        self.show()

    def remove(self, e):
        if not self.info or self.busy:
            return
        x, y = self.point(e)
        for i in range(len(self.regions) - 1, -1, -1):
            r = self.regions[i]
            a, b, c, d = r['rect']
            if r['page'] == self.page and a <= x <= c and (b <= y <= d):
                self.regions.pop(i)
                self.invalidate()
                self.show()
                break

    def close(self):
        self.data = None
        self.root.destroy()
