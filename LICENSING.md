# Original application code: GNU AGPL version 3

With the owner's authorization on 2026-10-15, the original PDF Redactor application code in `app/`, its original tests, and original packaging and verification scripts in this candidate are released under the GNU Affero General Public License, **version 3 only** (SPDX `AGPL-3.0-only`). The complete license is in `LICENSE`. You may use, modify and redistribute the covered code under that license. It is provided without warranty, as stated in the license.

The application resource files copied into `app/` are included in this original-work grant to the extent the owner holds rights in them. Third-party libraries, fonts, source archives, upstream code and Microsoft runtime components retain their own applicable licenses; this grant does not replace those terms or claim their copyrights.

This directory is an isolated source and packaging candidate. Licensing the original code does not make an incomplete native-source offer complete or clear an installer for distribution. The evaluated 0.9.0 installer and historical source archives remain unchanged; they do not contain these new original-code license headers.

Before a binary is delivered under this route, its covered source must match the actual build and include the applicable build/install material and license notices. This candidate uses the official PyMuPDF 1.28.2 wheel, whose native metadata explicitly records the matching MuPDF 1.28.2 source release. That native source matches the publisher's SHA-256, and the exact Python-wrapper commit matches the wheel's Python files. Regression and independent review evidence is recorded separately. No private PDFs, exported PDFs, credentials or private QA belong in a distributable.
