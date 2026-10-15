# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Windowed entry point; PDF work always uses the separate console-subsystem worker."""
import json,sys
from pathlib import Path
from best_effort_controller import call_best_effort_worker
VERSION='0.9.2'
def main():
 if sys.argv[1:2]==['--self-test']:
  if len(sys.argv)!=3:raise ValueError('Self-test requires one output path.')
  result=dict(version=VERSION,windowed_entry_executed=True,gui_constructed=False,worker=call_best_effort_worker(b'','health'))
  Path(sys.argv[2]).write_text(json.dumps(result,indent=2));return
 import tkinter as tk
 from tkinter import messagebox
 from best_effort_app import BestEffortApp
 root=tk.Tk();root.withdraw()
 app=BestEffortApp(root);root.title(f'PDF Redactor Best Effort {VERSION}')
 menu=tk.Menu(root);help_menu=tk.Menu(menu,tearoff=False)
 help_menu.add_command(label='About',command=lambda:messagebox.showinfo('PDF Redactor Best Effort',f'Version {VERSION} - evaluation candidate\nCopyright (C) 2026 PDF Redactor contributors.\nGNU AGPL version 3; provided without warranty.\nYou may modify and redistribute under LICENSE.\nMatching source: see SOURCE-INFO.txt beside the app.\nProcesses PDFs locally and offline; inspect all exports.\nThird-party terms are in ThirdPartyNotices.'))
 menu.add_cascade(label='Help',menu=help_menu);root.configure(menu=menu)
 root.deiconify();root.mainloop()
if __name__=='__main__':main()
