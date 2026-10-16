# PDF Redactor Best Effort: user guide

[Back to README](../README.md) · [Download v0.9.2 evaluation](https://github.com/TarronKay/pdf-redactor-best-effort/releases/tag/v0.9.2-evaluation)

This guide covers the Windows **0.9.2 evaluation** interface: opening a PDF, setting redactions, choosing an output mode and saving the result. Documents are processed locally, without uploads.

**[Watch the 75-second narrated walkthrough](https://raw.githubusercontent.com/TarronKay/pdf-redactor-best-effort/main/docs/media/redactor-professional-walkthrough-Wyatt.mp4)** · [Captions (SRT)](media/redactor-professional-walkthrough-captions.srt)

## Make a redacted copy

1. **Open the document.** Click **Select PDF**, choose a file and wait for the first-page preview. The app accepts PDFs up to **20 MiB** with **1–30 pages**. Use an unlocked copy if the PDF requires a password.
2. **Enter known identifiers.** Add names, IDs or other strings under **Known identifiers (one per line)**. Suggestions refresh automatically after a short pause and ignore letter case. Current identifiers and suggestion settings carry over when you open another document.
3. **Set the suggestion options.** **Remove institution** and **Remove test dates** are enabled by default. **Refresh suggestions** runs the analysis immediately. Existing boxes remain selected when these settings or identifiers change.
4. **Adjust the boxes.** Use **Show redacted page (black boxes)** to switch between the original page with colored selection overlays and the redacted preview. Left-drag to add a box; right-click inside a box to remove it. Both actions work in either view when processing has finished. To change a box's size, remove it and draw another. Use **Previous**, **Next** and the vertical scrollbar to work through the document.
5. **Choose the output mode.** Open **Advanced options**, then select **Selectable text (best effort)** or **Image-only (no text layer)**. The differences are described [below](#choose-an-output-mode).
6. **Export the copy.** Click **Export redacted copy**, choose a `.pdf` filename and destination folder, and wait for the saved-file message. **Mark checked (optional)** is available as a page progress marker; using it is not a prerequisite for export.
7. **Locate the output.** The status message identifies the PDF, its `.verification.json` report and the folder where both were saved. Open the named PDF from that folder. Existing filenames receive a numeric suffix, so a new export may be called `redacted-copy-1.pdf` rather than `redacted-copy.pdf`.

## Interface map

![Numbered interface map: file and page buttons, suggestion options, identifier entry, advanced output modes, status and page canvas.](images/interface-map.png)

*Numbered map of the 0.9.2 controls, drawn from the source interface. This is a schematic, not a native GUI screenshot. Numbers correspond to the control reference below.*

### Example: original and exported copy

![Fictional PDF before and after export: name, ID, institution, date, image area and repeated footer identifier are covered, while the educational content remains visible.](images/synthetic-output.png)

*Actual PDF renderings from a fictional two-page example, with the first page shown before and after export. The selection combines automatic suggestions and a manual box. Selectable-text output is pictured.*

## Control reference

| Map | Control | What it does |
| --- | --- | --- |
| 1 | **Select PDF** | Opens a file picker. A new file resets the page, boxes and checked-page markers; current identifiers, suggestion settings and output mode are retained. Cancel leaves the current document open. |
| 2 | **Refresh suggestions** | Repeats analysis using the current identifiers and settings, adding suggestions while preserving existing boxes. |
| 3 | **Previous** | Moves back one page, stopping at the first page. |
| 4 | **Next / Last page** | Moves forward one page. At the end of the document, the label becomes **Last page** and the button is disabled. |
| 5 | **Clear page regions** | Labeled **Clear page redactions** in the walkthrough. Removes all boxes on the displayed page, including manual boxes and suggestions. Other pages are unchanged. There is no undo; a later refresh can add suggestions back. |
| 6 | **Mark checked (optional)** | Records a progress marker for the displayed page without advancing it. It is available with a current redacted preview; changes to the selection, settings or mode can clear the marker. |
| 7 | **Export redacted copy** | Exports the whole document with the current boxes and output mode, producing a new PDF/report pair. The button is paused during processing and identifier updates. Canceling the save dialog saves nothing. |
| 8 | **Remove institution** | Enables institution suggestions based on recognized labels or header patterns. Enabled by default. Unticking it leaves existing boxes in place. |
| 9 | **Remove test dates** | Enables suggestions for labeled test/exam/administration dates and matching numeric dates, including history dates. Enabled by default. Unticking it leaves existing boxes in place. |
| 10 | **Show redacted page (black boxes)** | Switches between the redacted preview and the original page with selection overlays. Enabled by default. It changes the display, not the selected boxes or output mode. |
| 11 | **Known identifiers (one per line)** | Accepts names, IDs or other strings, ignoring blank lines and surrounding whitespace. Edits refresh suggestions automatically. Matching ignores letter case; terms longer than 200 characters are unsupported by the matching path. |
| 12 | **Advanced options** | Shows or hides the output-mode radio buttons. Hiding the panel retains the selected mode. |
| 13 | **Selectable text (best effort)** | The default output mode: rendered page images with a newly reconstructed, invisible searchable text layer. |
| 14 | **Image-only (no text layer)** | Outputs rendered page images without a searchable text layer. Text selection, copying and screen-reader access to page text are unavailable. |
| 15 | **Mode warning and status message** | Shows the current mode, processing progress, page number, document-wide box count, optional checked-page count, messages and saved-file location. |
| 16 | **Page canvas and vertical scrollbar** | Displays the current page. Left-drag adds a box; right-click removes the newest overlapping box at that point. Both work in the original and redacted views while the app is ready. Boxes follow the displayed orientation. A page change or preview refresh returns the scroll position to the top. |
| 17 | **Help → About** | Shows the release version, license information and location of matching source and third-party terms. |
| — | **Window close (X)** | Closes the application. Selections are not stored as a reusable project/session, so opening the original again starts a new session. |

The identifier field remains editable while other controls may be paused for processing. The interface has no dedicated zoom, rotate, page-jump, batch-export, box-resize or undo controls.

## Working with suggestions and boxes

Suggestions use native PDF text: identifier labels such as `Name:` and `Student ID:`, email/phone patterns, long numeric identifiers, the institution/date options and supplied terms. Recognized layouts can also contribute identifier-block suggestions. A suggestion may cover an entire line; right-click and redraw if a smaller selection is preferable.

Refreshes are additive. For example, removing `Alex Example` from the identifier field leaves any box already covering that name in place. To reduce the selection, remove individual boxes or use **Clear page regions** and redraw. Refreshing later may add those suggestions again. Reopening the PDF resets all boxes and checked-page markers.

In the original view, colored overlays identify the selected regions. In the redacted view, the selected areas appear black with red outlines. Tiny drags of two PDF points or less in either dimension are ignored. Pictures, scanned text, handwriting and codes can be covered with manual boxes.

## Choose an output mode

| | Selectable text (best effort) | Image-only (no text layer) |
| --- | --- | --- |
| Appearance | Rendered pages with the selected areas blacked out | Rendered pages with the selected areas blacked out |
| Search and copy | A new text layer reconstructed from eligible printable ASCII words | No extractable page text |
| Useful when | You want to retain text search/copy functionality | You need the page appearance without selectable text |
| Text handling | A selected rectangle's intersection with a word removes that whole word from the reconstructed layer. Hidden or unselected identifying text may remain in that layer. Non-ASCII or otherwise ineligible words may be omitted, and text order/alignment can differ from the original. | All page content is represented as images. |

**Best Effort note:** Automatic suggestions may miss identifiers. Selectable output retains a text layer; image-only output does not. Scanned text is not detected automatically because the app does not use OCR.

Both modes create a fresh PDF. Source metadata, attachments, annotation/form/action objects, bookmarks, source IDs and earlier revisions are not copied. Visible form and annotation appearances become page pixels; their original interactive objects are not retained.

## Output files and location

Choosing `redacted-copy.pdf` normally produces these two files in the selected folder:

```text
redacted-copy.pdf
redacted-copy.verification.json
```

If either filename exists, the app uses the first free numbered pair, such as `redacted-copy-1.pdf` and `redacted-copy-1.verification.json`. The original and existing outputs are preserved. The status message gives the actual names and location.

The PDF is the exported document. The JSON is a technical record of the export mode, input/output hashes, page and box counts, optional checked-page count, integrity checks and text diagnostics. It includes the number of known-identifier terms, not their literal values or the source pathname. It can be retained alongside the PDF as an export record.

If you make further adjustments in the app, export again to create another pair; an earlier exported PDF does not update automatically.

<details>
<summary>Understanding the verification report</summary>

The report status is `BEST_EFFORT_EXPORTED_INTEGRITY_CHECKS_PASSED_CHECK_CONTENT`. It records successful engine checks on the generated PDF structure and selected black pixels. `mandatory_review` is `false`, and `pages_marked_checked` records the optional progress markers. The `text_diagnostics` entries describe extractor agreement and text-box alignment; they are diagnostic rather than mandatory export gates.

</details>

## Troubleshooting

| Message or behavior | Next step |
| --- | --- |
| **Cannot open PDF / file-size or page-count limit** | Use a PDF up to 20 MiB with 1–30 pages. Large page dimensions or rendering/word budgets can also exceed local resource limits. |
| **This PDF needs a password** | Open an unlocked copy; the app has no password-entry control. |
| **Little or no searchable text / unrecognized layout or images / incomplete suggestions** | Continue with manual boxes for content that was not suggested. Best Effort can export unfamiliar layouts and image-based pages. |
| Boxes remain after an identifier or setting changes | Remove them individually or clear the current page. Refreshes preserve the existing selection. |
| **Mark checked** is disabled | Wait for preparation and enable **Show redacted page**. This marker requires a current redacted preview. |
| **Export** is disabled / updates are pending | Wait for processing and identifier updates to finish. The status message identifies preparation errors. |
| **Preview unavailable** | Read the status detail. Export can still be attempted; the engine runs its output checks independently. |
| **Source changed / settings changed / output differs from current preview** | Reselect the source if requested, or refresh the current settings and export again. |
| **Worker failed / local resource bounds / exceeded 60 seconds** | Try a smaller or simpler input. These messages indicate a processing size, memory, CPU or time limit. |
| **Installed processing worker is missing** | Repair or reinstall the release through the normal installation process. |
| **Output integrity verification failed; nothing was saved** | No new output was saved. Try a simpler input or a different redaction workflow if the error persists. |
| **Export failed / choose a .pdf destination / access error** | Choose a writable folder, a `.pdf` suffix and an available destination with enough space. |
| Useful text is missing from search/copy or appears out of order | This reflects the selectable-text reconstruction described in the mode comparison. The page appearance and reconstructed text are separate parts of the output. |

## Version and illustration notes

The control reference follows [v0.9.2-evaluation](https://github.com/TarronKay/pdf-redactor-best-effort/tree/v0.9.2-evaluation), source commit `93e41b2e4ba1b7b1415ff437209e826202a36ab6`. The interface map is a schematic with [editable SVG source](images/interface-map.svg); the PDF example uses fictional content. Neither figure is a native GUI screenshot.

The video uses cropped interface captures with arrows and a fictional example of manual selection. It is separate from the interface map and PDF illustration above.

<details>
<summary>Source and documentation verification</summary>

Behavior is documented from the [GUI entry point](../app/release_gui.py), [Best Effort app](../app/best_effort_app.py), [workflow](../app/ui_workflow.py), [canvas controls](../app/ui_base.py), [output engine](../app/best_effort_engine.py) and [file naming](../app/export_files.py).

Documentation tests exercised the source GUI with its window withdrawn, including preparation, previews, control states, suggestions, progress markers, navigation, drawing/removal, modes and PDF/report export. Two-page synthetic exports passed required integrity checks in both modes. This used the available PyMuPDF 1.28.0 runtime; the frozen release uses 1.28.2. Native screenshot capture and interactive installer validation were outside that test coverage. Build and evaluation details are in [BUILDING.md](../BUILDING.md).

</details>
