# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Literal Unicode casefold matches mapped back to original native glyph boxes.

No OCR, accent removal, transliteration or guessed encoding correction.
The caller unions these with MuPDF's existing cross-line/dehyphenation matches.
"""
import pymupdf as fitz

def folded_identifier_rects(page,terms):
    needles=list(dict.fromkeys(term.strip().casefold() for term in terms if term.strip()))
    if not needles:return []
    found=[];seen=set();budget=0
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines',[]):
            folded=[];boxes=[]
            for span in line['spans']:
                for char in span['chars']:
                    value=char['c'].casefold();folded.append(value)
                    boxes.extend([char['bbox']]*len(value));budget+=len(value)
                    if budget>200000:raise ValueError('Native text matching budget exceeded.')
            text=''.join(folded)
            for needle in needles:
                start=0
                while True:
                    pos=text.find(needle,start)
                    if pos<0:break
                    rect=fitz.Rect(boxes[pos])
                    for box in boxes[pos+1:pos+len(needle)]:rect|=fitz.Rect(box)
                    rect&=page.rect
                    key=tuple(rect)
                    if not rect.is_empty and not rect.is_infinite and key not in seen:found.append(rect);seen.add(key)
                    if len(found)>2000:raise ValueError('Too many identifier matches.')
                    start=pos+1
    return found
