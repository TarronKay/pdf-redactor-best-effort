# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Local destructive redaction followed by a new, image-only document.
No input PDF object is copied into the deliverable. Never certifies anonymity.
"""
import hashlib, json, math, re
from pathlib import Path
import pymupdf as fitz
from identifier_matching import folded_identifier_rects
fitz.TOOLS.set_small_glyph_heights(True)
MAX_BYTES=20*1024*1024
MAX_PAGES=30
MAX_SIDE=1200
MAX_PIXELS=12_000_000
class Rejected(ValueError): pass
def image_fingerprint(doc,xref):
    """Includes decoded geometry/components and effective transparency mask."""
    if not xref or doc.xref_get_key(xref,'Mask')[0]!='null': return None
    pix=fitz.Pixmap(doc,xref)
    kind,value=doc.xref_get_key(xref,'SMask')
    if kind=='xref':
        mask=fitz.Pixmap(doc,int(value.split()[0]))
        pix=fitz.Pixmap(pix,mask)
    elif kind!='null': return None
    header=json.dumps([pix.width,pix.height,pix.n,pix.alpha,pix.colorspace.name if pix.colorspace else None]).encode()
    return hashlib.sha256(header+b'\0'+pix.samples).hexdigest()
SAFE_IMAGES=json.loads(Path(__file__).with_name('safe_images.json').read_text())
def open_pdf(data):
    if not 0<len(data)<=MAX_BYTES or not data.startswith(b'%PDF-'):
        raise Rejected('Requires a PDF under 20 MiB.')
    try: doc=fitz.open(stream=data,filetype='pdf')
    except Exception: raise Rejected('Malformed or unsupported PDF.') from None
    if doc.needs_pass or doc.is_encrypted or doc.metadata.get('encryption'):
        doc.close(); raise Rejected('Encrypted PDFs are unsupported, including empty-password encryption.')
    if doc.is_repaired or not 1<=len(doc)<=MAX_PAGES:
        doc.close(); raise Rejected('Repaired/malformed PDFs or more than 30 pages are unsupported.')
    for page in doc:
        page.set_rotation(0) # one coordinate system for extraction, preview and output
        if not all(math.isfinite(v) for v in page.rect) or min(page.rect.width,page.rect.height)<20 or max(page.rect.width,page.rect.height)>MAX_SIDE:
            doc.close(); raise Rejected('Page dimensions outside supported bounds.')
    return doc
DIRECT=re.compile(r'(?i)\b(?:name|examinee\s*id|student\s*id|id|date\s*of\s*birth|dob|email|e-mail|phone|address|registration\s*id)\s*:')
INDIRECT=re.compile(r'(?i)\b(?:test\s*date|exam\s*date|administration\s*date)\s*:')
EMAIL=re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
PHONE=re.compile(r'(?<!\d)(?:\+\d{1,3}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)')
MACHINE=re.compile(r'(?i)\bLABEL\d+\b|\b\d{8,}\b')
NUMERIC_DATE=re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
def analyze(data, institution=True, dates=True, terms=()):
    doc=open_pdf(data)
    pages=[]; proposals=[]; blockers=[]
    # Inline images cannot be bound safely to an authoritative resource/mask.
    inline_images=any(re.search(rb'(?<!\S)BI(?=\s)',doc.xref_stream(xref) or b'') for xref in range(1,doc.xref_length()) if doc.xref_is_stream(xref) and doc.xref_get_key(xref,'Subtype')[1]=='/Form')
    alltext='\n'.join(p.get_text() for p in doc)
    title=doc[0].get_text().upper()
    category='CAS' if 'CUSTOMIZED ASSESSMENT SERVICES' in title else 'CBSE' if 'COMPREHENSIVE BASIC SCIENCE EXAMINATION' in title else 'CBSSA' if 'CBSSA' in title else 'CBSE' if 'CBSE' in title else 'Unknown / synthetic'
    for i,page in enumerate(doc):
        text=page.get_text()
        images=page.get_image_info(xrefs=True)
        resource_images=page.get_images(full=True)
        if len(text.strip())<40: blockers.append(f'Page {i+1}: image-only or insufficient extractable text; no reliable OCR.')
        # Any input raster may contain a barcode, QR code or visible identity.
        inline=inline_images or bool(re.search(rb'(?<!\S)BI(?=\s)',page.read_contents()))
        # Placement xrefs are resolved by base-image hashes in MuPDF and may
        # alias objects with distinct masks. Inspect every actual resource too.
        if inline or (images and not resource_images) or any(image_fingerprint(doc,item[0]) not in SAFE_IMAGES for item in resource_images) or any(not item.get('xref') for item in images):
            blockers.append(f'Page {i+1}: unrecognized raster images require unsupported OCR/barcode review; export blocked.')
        if any(x.get('type')=='fill-path' and len(x.get('items',[]))>200 for x in page.get_drawings()):
            blockers.append(f'Page {i+1}: complex vector artwork; possible machine-readable identifiers require review.')
        pages.append(dict(width=page.rect.width,height=page.rect.height))
        # Lines are conservative suggestions; multi-column lines may need adjustment.
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                value=''.join(s['text'] for s in line['spans'])
                reason=None
                if DIRECT.search(value): reason='direct identifier label'
                elif EMAIL.search(value) or PHONE.search(value): reason='contact details'
                elif MACHINE.search(value): reason='machine-readable / long identifier'
                elif dates and INDIRECT.search(value): reason='test date (configured)'
                elif institution and line['bbox'][1]<200 and re.search(r'(?i)\b\d{6}\s*-|institution\s*:',value): reason='institution (configured)'
                if reason:
                    r=fitz.Rect(line['bbox'])+(-2,-2,2,2)
                    proposals.append(dict(page=i,rect=list(r & page.rect),reason=reason))
        seen=set()
        for term in terms:
            if not isinstance(term,str) or len(term)>200: raise Rejected('Invalid search term.')
            if term.strip():
                for rect in page.search_for(term):
                    box=list((rect+(-2,-2,2,2)) & page.rect)
                    if tuple(box) not in seen:
                        proposals.append(dict(page=i,rect=box,reason='user-supplied term'));seen.add(tuple(box))
        try:
            folded=folded_identifier_rects(page,terms)
        except ValueError as error:raise Rejected(str(error)) from None
        for rect in folded:
            box=list((rect+(-2,-2,2,2)) & page.rect)
            if tuple(box) not in seen:
                proposals.append(dict(page=i,rect=box,reason='user-supplied term'));seen.add(tuple(box))
        if dates:
            for value in set(NUMERIC_DATE.findall(text)):
                for rect in page.search_for(value):
                    proposals.append(dict(page=i,rect=list((rect+(-1,-1,1,1)) & page.rect),reason='numeric date including history (configured)'))
    doc.close()
    if len(proposals)>2000: raise Rejected('Too many suggested redactions.')
    return dict(category=category,pages=pages,regions=proposals,blockers=blockers,sha256=hashlib.sha256(data).hexdigest())
def validate_regions(doc,regions):
    if not isinstance(regions,list) or len(regions)>2000: raise Rejected('Invalid region count.')
    result=[]
    for item in regions:
        i=item['page']; values=item['rect']
        if type(i) is not int or not 0<=i<len(doc) or len(values)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values): raise Rejected('Invalid region.')
        r=fitz.Rect(values)
        if r.is_empty or r.is_infinite or not doc[i].rect.contains(r): raise Rejected('Region outside page.')
        result.append((i,r))
    return result
