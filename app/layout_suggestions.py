# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Advisory layout boxes only; no strict native/hybrid export or asset trust."""
import re
import pymupdf as fitz
from engine import Rejected
PROFILES = {'CBSE': dict(pages=3, width=612, height=792, regions=[[(380, 120, 590, 141), (30, 265, 590, 515)], [(380, 120, 590, 141), (30, 465, 590, 590)], [(380, 120, 590, 141), (30, 200, 590, 680)]], anchors=['Your CBSE', 'Performance by Physician Task', 'Pathology']), 'CBSSA': dict(pages=8, width=612, height=792, regions=[[(30, 115, 585, 490)], [(30, 305, 585, 470)], [(30, 120, 585, 530)], [(30, 120, 585, 535)], [(30, 240, 585, 760)], [(30, 465, 585, 760)], [(30, 145, 585, 760)], [(30, 145, 585, 760)]], anchors=['Total Equated Percent Correct', 'Performance by Physician Task', 'Performance by System', 'Performance by Discipline', 'Your Overall Performance History', 'PHYSICIAN TASK', 'SYSTEM', 'DISCIPLINE']), 'CAS': dict(pages=2, width=579.9600219726562, height=792, regions=[[(30, 320, 550, 720)], [(30, 210, 550, 520)]], anchors=['Total Test', 'Question-Level Feedback']), 'CAS Group Performance': dict(pages=8, width=792, height=612, regions=[[(36, 284, 756, 568)], [(36, 165, 756, 218)], [(260, 205, 756, 574)], [(260, 168, 351, 527)], [(34, 145, 756, 196), (34, 208, 625, 550)], [(36, 262, 756, 574)], [(36, 169, 756, 239)], [(36, 251, 756, 400)]], anchors=['Percent Correct Score Descriptive Statistics', 'Percent Correct Score Descriptive Statistics (Continued)', 'Roster of Percent Correct Scores', 'Roster of Percent Correct Scores (Continued)', 'Total Percent Correct Score Frequency Distribution', 'Source Comparisons', 'Source Comparisons (Continued)', 'Question-Level Feedback'], required_redactions={2: [(36, 245, 260, 574)], 3: [(36, 207, 260, 527)]}), 'CAS Scaled Group Performance': dict(pages=3, width=792, height=612, regions=[[(36, 204, 756, 352), (36, 390, 756, 540)], [(36, 160, 756, 438)], [(270, 162, 445, 284)]], anchors=['Score Descriptive Statistics', 'Score Frequency Distribution (Based on All Examinees Tested)', 'Content Area ID*'], required_redactions={0: [(594, 127, 758, 141), (34, 164, 181, 179), (707, 575, 768, 590), (36, 577, 75, 592), (688, 144, 760, 160)], 1: [(594, 78, 758, 92), (34, 114, 181, 129), (707, 575, 768, 590), (688, 95, 760, 111)], 2: [(36, 201, 270, 284), (597, 77, 760, 92), (34, 114, 181, 129), (707, 575, 768, 590), (690, 95, 760, 111)]})}

def fail(message):
    raise Rejected(message)

def profile(doc):
    text = doc[0].get_text().upper()
    text = re.sub('\\s+', ' ', text)
    kind = 'CAS Scaled Group Performance' if 'CUSTOMIZED EXAMINATION' in text and 'SCALED SCORE DESCRIPTIVE STATISTICS' in text else ('CAS Group Performance' if 'GROUP PERFORMANCE REPORT' in text else 'CAS' if 'EXAMINEE PERFORMANCE REPORT' in text else 'CAS unsupported subtype') if 'CUSTOMIZED ASSESSMENT SERVICES' in text else 'CBSE' if 'COMPREHENSIVE BASIC SCIENCE EXAMINATION' in text else 'CBSSA' if 'CBSSA' in text else None
    action = 'Use original-page view to inspect the report. Hybrid requires a reviewed report subtype and layout; select a reviewed sample or use raster mode and re-review every page if its separate checks pass.'
    if kind not in PROFILES:
        fail(f"Unsupported report subtype: {kind or 'unrecognized NBME report'}. " + action)
    spec = PROFILES[kind]
    if len(doc) != spec['pages'] or any((abs(p.rect.width - spec['width']) > 0.1 or abs(p.rect.height - spec['height']) > 0.1 for p in doc)):
        fail(f"{kind}: layout differs from reviewed sample (expected {spec['pages']} pages, {spec['width']:g} x {spec['height']:g} pt; found {len(doc)} pages). " + action)
    for page, anchor in zip(doc, spec['anchors']):
        if re.sub('\\s+', ' ', anchor).casefold() not in re.sub('\\s+', ' ', page.get_text()).casefold():
            fail(f'{kind}: page {page.number + 1} required educational layout anchor missing. ' + action)
    if kind == 'CAS Scaled Group Performance':
        page = doc[2]
        if not any((w[4] == 'ID' and abs(w[0] - 38.16) < 1 and (abs(w[1] - 190.556) < 1) for w in page.get_text('words'))) or not any((w[4] == 'Name' and abs(w[0] - 127.72) < 1 and (abs(w[1] - 190.556) < 1) for w in page.get_text('words'))):
            fail(f'{kind}: roster identifier-column anchors differ; separate layout review required.')
        if any((w[1] >= 201 and w[3] <= 284 and (w[0] < 270 < w[2]) for w in page.get_text('words'))):
            fail(f'{kind}: roster identifier columns cross the reviewed score boundary.')
        roster = fitz.Rect(36, 201, 270, 284)
        if any((w[1] >= 201 and w[1] < 550 and (w[0] < 270) and (not roster.contains(fitz.Rect(w[:4]))) for w in page.get_text('words'))):
            fail(f'{kind}: roster row extent exceeds the reviewed five-row identifier block; separate layout review required.')
    if kind == 'CAS Group Performance':
        for i in spec['required_redactions']:
            page = doc[i]
            header_y = {2: 233.54, 3: 194.642}[i]
            if not any((abs(r.x0 - 38.3) < 1 and abs(r.y0 - header_y) < 1 for r in page.search_for('Examinee ID'))) or not any((w[4] == 'Examinee' and abs(w[0] - 107.4) < 1 and (abs(w[1] - header_y) < 1) for w in page.get_text('words'))):
                fail(f'{kind}: roster identifier-column anchors differ on page {i + 1}; separate layout review required.')
            for word in page.get_text('words'):
                r = fitz.Rect(word[:4])
                if r.y0 >= 207 and r.y1 <= 574 and (r.x0 < 260) and (r.x1 > 260):
                    fail(f'{kind}: roster identifier columns extend into score columns on page {i + 1}; separate layout review required.')
    return (kind, spec)

def overlay_parameters(word):
    rect = fitz.Rect(word['rect'])
    height = rect.height
    unit = fitz.get_text_length(word['text'], fontname='helv', fontsize=1)
    base_ratio = rect.width / (unit * height)
    size = height / base_ratio
    ratio = base_ratio * base_ratio
    font = fitz.Font('helv')
    baseline = rect.y0 + height * font.ascender / (font.ascender - font.descender)
    return (fitz.Point(rect.x0, baseline), size, ratio)
