# PDF Redactor Best Effort 0.9.2

This is a separate Best Effort-only lean evaluation candidate. No legacy strict hybrid/native workers or owner-supplied scaled-sample fingerprints are included. Public sample image hashes remain only for advisory warnings; they do not gate Best Effort export. Advisory layout anchors/boxes and text placement math are retained for suggestions; they certify no anonymity.

## Source and dependencies

The complete matching source ZIP includes all app, synthetic tests, build/packaging scripts, notices and 37 exact official dependency source archives. See source-provenance/source-archives.json and official-wheel-lock.json for URLs/hashes. Vendor archives retain public fixtures, including PDF and test key/certificate files; no owner report is supplied. Third-party terms retain their own scope. Source/modification/redistribution rights for original covered code are GNU AGPL-3.0-only.

Use Windows 10/11 x64 and CPython 3.13.15. Create a fresh `build-env` and install `requirements-runtime-build.txt` with `--require-hashes`; use `requirements-test.txt` likewise for testing. Offline builds can obtain the exact official wheels first and use `--no-index --find-links`. No new dependency version is silently substituted.

The evaluated freeze uses official PyMuPDF 1.28.2 wheel SHA-256 ebd244918798502d7b4504c90410d1711a4d7675a32584ca30f1bab419ecbffe. Its wrapper commit12786d12b2962a1d77fd13b103162eddf749644c and MuPDF1.28.2 release sources are included. Native compilation has not been validated locally; no byte-identical reproduction is claimed.

`redactor.spec` selects/hash-checks three Microsoft runtime DLLs from the reviewed official release Redist path and excludes app-local UCRT/API-set copies. Supply legitimate runtime inputs under applicable compiler/Redist terms. Different paths/hashes require a recorded compatibility review. No acceptance/repair/bypass is automated. Python/Tcl/Tk and compiler/SDK are general-purpose host build inputs with separate requirements.

## Build and verify

In a fresh extracted source tree, use the configured environment's Python:

```
python -m pytest -q --basetemp build-test-temp
python build_frozen.py
python prepare_notices.py
python make_corresponding_source.py
python build_msi.py
```

The build writes only its local dist/work/artifact directories. Notice/source generators refuse existing output. MSI creation uses Windows makecab/MSI APIs and a read-only UI graph preflight; it does not execute setup, install/repair/remove, accept terms, elevate or change security. Two separate GUI and worker executables preserve process isolation. The worker imposes a Windows Job memory/CPU limit; controller timeout remains60seconds.

The lean MSI does not embed source. Installer and matching `PDFRedactor-0.9.2-CORRESPONDING-SOURCE.zip` must be adjacent free downloads at the exact versioned release named in SOURCE-INFO.txt. Verify both hashes, source closure and actual accessibility before publication/distribution. Git trees omit vendor archives; use the complete ZIP for this recipe. Never reuse prior0.9.1 hashes or imply prior installer lifecycle tests establish this rebuilt package's behavior.

For native modifications, unpack the pinned wrapper and MuPDF source safely, follow upstream setup.py/pyproject.toml and MuPDF Windows build scripts, and use the pinned requirements-native-tools.txt in a separately prepared legitimate compiler environment. Set PYMUPDF_SETUP_MUPDF_BUILD to the local MuPDF tree and PYMUPDF_SETUP_MUPDF_TGZ empty before `python -m pip wheel --no-deps --no-build-isolation --no-index <wrapper-tree> --wheel-dir <wheelhouse>`. This route was not locally validated. Re-freeze and fully revalidate modified native builds.

Inspect all exported pixels and two text extractors with synthetic/public files, including selected-word intersections, annotations/forms, rotated pages, hidden text and blank pages. Best Effort deliberately cannot prove hidden/occluded text absence. Full clean-computer setup lifecycle and live GUI testing are separate coverage gaps; no such execution is performed by packaging scripts. The release is unsigned and without warranty.
