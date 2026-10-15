# PDF Redactor Best Effort 0.9.2

Unsigned Windows 10/11 x64 evaluation candidate for local PDF redaction. This public build supports Best Effort selectable text and image-only output. Legacy strict hybrid/native reconstruction is excluded.

**Export does not prove anonymity.** Best Effort text may retain hidden, white, occluded, misplaced or unselected identifying text. Image-only output omits searchable text but still needs complete visible selection. Inspect every exported page and its searchable text before sharing. Page checking is optional. Processing stays local; no cloud OCR or upload is used. No NBME affiliation or endorsement is claimed.

## Installer and exact matching source

Proposed release: [v0.9.2-evaluation](https://github.com/TarronKay/pdf-redactor-best-effort/releases/tag/v0.9.2-evaluation).

- `PDFRedactor-BestEffort-0.9.2-x64-EVALUATION.msi`: lean installer.
- `PDFRedactor-0.9.2-CORRESPONDING-SOURCE.zip`: complete matching app, tests, packaging/build scripts, pinned dependency sources and notices.

The release must provide both assets adjacent at no charge. The MSI omits embedded source; installed SOURCE-INFO.txt gives the exact versioned release and source filename. This local candidate does not claim that hosting is already available. GitHub's automatically generated repository archives omit large upstream archives and are not the complete corresponding-source package. Use the complete ZIP and [BUILDING.md](BUILDING.md) to build or modify it. The ZIP's 37 official vendor archives retain public fixtures including PDFs and test keys/certificates; owner PDFs, private QA and owner-supplied scaled-sample asset fingerprint allowlists are excluded.

## Behavior and evaluation limits

Exports use fresh rendered page pixels, outward black redaction boxes and a new PDF object graph, with optional reconstructed printable ASCII text. Any selected word intersection removes that whole word from the reconstructed layer. Visible annotation/form appearances become pixels. The output does not copy the original PDF metadata, attachments, forms or actions. New numbered PDF/JSON pairs preserve original files.

Public sample image hashes remain only for advisory warnings. The Best Effort engine, advisory layout suggestions, redaction geometry, optional checking and stale-state protections are retained. Strict report/font/image eligibility gates are removed with the excluded legacy modes; their claims do not apply to Best Effort. Inputs are limited to 20 MiB and 1–30 pages. Windows worker memory/CPU limits and controller timeouts remain enforced.

Source regressions, independent synthetic old/new comparisons, headless constructor/thread checks and frozen-runtime checks are recorded separately during candidate review. They do not establish successful full installation, repair, removal or end-to-end GUI use on a clean recipient computer. No live installer or GUI session is run for this candidate. Native compilation of the included MuPDF source has not been validated locally; the freeze uses the pinned official PyMuPDF 1.28.2 wheel. The installer and executables are unsigned.

Original code, tests and packaging are [AGPL-3.0-only](LICENSE), without warranty. Third-party licenses and Microsoft runtime terms remain separate; see [LICENSING.md](LICENSING.md) and `notices/`. Recipients retain modification and redistribution rights for the covered work.
