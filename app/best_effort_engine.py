# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 PDF Redactor contributors.
"""Generic local pixel redaction; recognition and checking are advisory.

Source PDF objects are never copied. Optional extracted text is best effort,
not a proof that hidden, clipped, occluded or identifying text is absent.
"""
import hashlib,io,json,math,re
import pymupdf as fitz
from PIL import Image,ImageDraw
from pypdf import PdfReader
from engine import MAX_BYTES,MAX_PAGES,MAX_PIXELS,Rejected,validate_regions,analyze as legacy_analyze
from layout_suggestions import profile,overlay_parameters
from preview_cache import cache_key

MODES={'best-effort-text','best-effort-raster'}
MAX_TOTAL_PIXELS=100_000_000

def finish(doc):
    doc.set_metadata({})
    pages=doc.xref_get_key(doc.pdf_catalog(),'Pages')[1]
    doc.update_object(doc.pdf_catalog(),f'<< /Type /Catalog /Pages {pages} >>')
    for page in doc:
        for row in page.get_images():doc.xref_set_key(row[0],'ColorSpace','/DeviceRGB')
    return doc.tobytes(garbage=4,deflate=True,clean=False,no_new_id=True)

def add_page(output,width,height,pix,words):
    target=output.new_page(width=width,height=height)
    target.insert_image(target.rect,stream=pix.tobytes('png'))
    for word in words:
        origin,size,ratio=overlay_parameters(word)
        target.insert_text(origin,word['text']+' ',fontname='helv',fontsize=size,render_mode=3,morph=(origin,fitz.Matrix(ratio,1)))

def fresh_graph(payload,doc,records):
    # Canonical regeneration permits only one RGB image and the recorded new
    # Helvetica words per page. Extra objects/keys/streams/metadata change bytes.
    reference=fitz.open()
    try:
        if len(doc)!=len(records):return False
        for page,words in zip(doc,records):
            images=page.get_images()
            if len(images)!=1:return False
            pix=fitz.Pixmap(doc,images[0][0])
            if pix.n!=3 or pix.alpha:return False
            add_page(reference,page.rect.width,page.rect.height,pix,words)
        return finish(reference)==payload
    except Exception:return False
    finally:reference.close()

def open_renderable(data):
    if not isinstance(data,bytes) or not 0<len(data)<=MAX_BYTES:raise Rejected('Requires a PDF under 20 MiB.')
    try:doc=fitz.open(stream=data,filetype='pdf')
    except Exception:raise Rejected('PDF could not be opened.') from None
    try:
        if not doc.is_pdf:raise Rejected('The selected file is not a PDF.')
        if doc.needs_pass:raise Rejected('This PDF needs a password. Open an unlocked copy.')
        if not 1<=len(doc)<=MAX_PAGES:raise Rejected('Local resource limit: 1 to 30 pages per file.')
        total=0
        for page in doc:
            r=page.rect
            if not all(math.isfinite(v) for v in r) or r.width<=0 or r.height<=0:raise Rejected('Invalid page geometry.')
            w,h=math.ceil(r.width*2),math.ceil(r.height*2)
            if max(w,h)>20000 or w*h>MAX_PIXELS:raise Rejected('Page exceeds the local rendering pixel budget.')
            total+=w*h
        if total>MAX_TOTAL_PIXELS:raise Rejected('File exceeds the local total rendering pixel budget.')
        return doc
    except Exception:doc.close();raise

def analyze(data,institution=True,dates=True,terms=()):
    doc=open_renderable(data)
    try:
        pages=[dict(width=p.rect.width,height=p.rect.height) for p in doc]
        warnings=[];regions=[];category='Unrecognized layout - manual use'
        if doc.is_repaired:warnings.append('Renderer repaired the input; inspect page appearance carefully.')
        try:
            old=legacy_analyze(data,institution,dates,terms)
            regions=[dict(r,rect=list(fitz.Rect(r['rect'])*doc[r['page']].rotation_matrix)) for r in old['regions']]
            warnings.extend(s.replace('export blocked.','inspect manually.').replace('require unsupported OCR/barcode review','need manual image/barcode inspection') for s in old['blockers'])
        except Exception:
            warnings.append('Automatic suggestions were incomplete; manual redactions and export remain available.')
        try:
            kind,spec=profile(doc);category=kind
            for i,boxes in spec.get('required_redactions',{}).items():
                regions.extend(dict(page=i,rect=list(fitz.Rect(b)*doc[i].rotation_matrix),reason='suggested identifier block (optional)') for b in boxes)
        except Exception:warnings.append('Layout is unrecognized or differs from a sample; inspect all identifiers manually.')
        if any(len(p.get_text().strip())<40 for p in doc):warnings.append('Some pages have little or no searchable text. No OCR is performed.')
        return dict(sha256=hashlib.sha256(data).hexdigest(),pages=pages,category=category,regions=regions,blockers=[],warnings=list(dict.fromkeys(warnings)),mode='best-effort')
    finally:doc.close()

def pixel_boxes(page,pix,regions,index):
    sx,sy=pix.width/page.rect.width,pix.height/page.rect.height
    return [(max(0,math.floor(r.x0*sx)),max(0,math.floor(r.y0*sy)),min(pix.width,math.ceil(r.x1*sx)),min(pix.height,math.ceil(r.y1*sy))) for p,r in regions if p==index]

def render_redacted(page,index,regions):
    # Visible annotation/widget appearances are flattened into pixels. Their
    # interactive objects, comments, authors and actions are not copied.
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False,annots=True)
    image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples);draw=ImageDraw.Draw(image)
    boxes=pixel_boxes(page,pix,regions,index)
    for a,b,c,d in boxes:
        if c<=a or d<=b:raise Rejected('A selected redaction is too small to apply.')
        draw.rectangle((a,b,c-1,d-1),fill=(0,0,0))
    if any(image.crop(box).getbbox() is not None for box in boxes):raise Rejected('Selected pixel redactions did not apply.')
    return fitz.Pixmap(fitz.csRGB,pix.width,pix.height,image.tobytes(),False)

def extracted_words(page,index,regions):
    records=[];skipped=0
    # This is deliberately a heuristic, not the old strict visibility proof.
    # Obvious invisible painters are excluded; clipping/occlusion/font meaning
    # are not proven and residual searchable identifiers may remain.
    try:invisible=[fitz.Rect(c[3])*page.rotation_matrix for t in page.get_texttrace() if t['type']==3 or t['opacity']==0 for c in t['chars'] if c[0]!=32]
    except Exception:invisible=[]
    words=page.get_text('words',sort=True)
    if len(words)>20000:raise Rejected('Page exceeds the local extracted-word budget.')
    for item in words:
        text=item[4];rect=fitz.Rect(item[:4])*page.rotation_matrix
        if not text.isascii() or not 0<len(text)<=200 or any(ord(c)<33 or ord(c)>126 for c in text) or not page.rect.contains(rect) or rect.is_empty:
            skipped+=1;continue
        # Never reintroduce a whole original word that intersects a chosen box.
        if any(p==index and rect.intersects(box) for p,box in regions) or any(rect.intersects(box) for box in invisible):skipped+=1;continue
        record=dict(text=text,rect=list(rect))
        try:
            origin,size,ratio=overlay_parameters(record)
            if not all(math.isfinite(v) for v in [origin.x,origin.y,size,ratio]) or not .2<=ratio<=5 or not 3<=size<=40:skipped+=1;continue
        except Exception:skipped+=1;continue
        records.append(record)
    return records,skipped

def build(data,regions,mode):
    if mode not in MODES:raise Rejected('Unknown output mode.')
    source=open_renderable(data);output=fitz.open();records=[];hashes=[];skipped=[];sizes=[]
    try:
        checked=validate_regions(source,regions)
        for i,page in enumerate(source):
            pix=render_redacted(page,i,checked)
            words,count=extracted_words(page,i,checked) if mode=='best-effort-text' else ([],0)
            add_page(output,page.rect.width,page.rect.height,pix,words)
            records.append(words);skipped.append(count);hashes.append(hashlib.sha256(pix.samples).hexdigest());sizes.append([pix.width,pix.height])
        payload=finish(output)
        if len(payload)>100*1024*1024:raise Rejected('Output exceeds the local 100 MiB limit.')
        checks=verify(payload,records,hashes,sizes,regions,mode)
        diagnostics={key:checks.pop(key) for key in ['exact_generated_text_in_two_extractors','text_boxes_aligned']}
        if not all(checks.values()):raise Rejected('Output integrity verification failed; nothing was saved.')
        return payload,checks,dict(records=records,skipped=skipped,hashes=hashes,sizes=sizes,text_diagnostics=diagnostics)
    finally:source.close();output.close()

def verify(payload,records,hashes,sizes,regions,mode):
    doc=fitz.open(stream=payload,filetype='pdf');reader=PdfReader(io.BytesIO(payload),strict=True)
    try:
        root=reader.trailer['/Root']
        checks=dict(page_count=len(doc)==len(records)==len(reader.pages),no_document_info=reader.metadata is None and '/Info' not in reader.trailer,no_xmp=not doc.get_xml_metadata() and '/Metadata' not in root,no_source_ids='/ID' not in reader.trailer,no_attachments=doc.embfile_count()==0 and '/Names' not in root,no_forms='/AcroForm' not in root,no_annotations=all(not p.get('/Annots') for p in reader.pages),fresh_single_revision=payload.count(b'%%EOF')==1 and '/Prev' not in reader.trailer,no_actions_or_other_catalog_data=set(root)=={'/Type','/Pages'},fresh_allowlisted_objects=fresh_graph(payload,doc,records))
        sequences=True;black=True;pixel_hashes=True;aligned=True;only_layer=True
        for i,(page,other) in enumerate(zip(doc,reader.pages)):
            expected=[r['text'] for r in records[i]]
            sequences &= page.get_text().split()==(other.extract_text() or '').split()==expected
            actual=page.get_text('words')
            aligned &=len(actual)==len(records[i]) and all(max(abs(a-b) for a,b in zip(w[:4],r['rect']))<.2 for w,r in zip(actual,records[i]))
            only_layer &=all(t['type']==3 and t['font']=='Helvetica' for t in page.get_texttrace())
            images=page.get_images()
            if len(images)!=1:pixel_hashes=False;continue
            pix=fitz.Pixmap(doc,images[0][0]);pixel_hashes &= [pix.width,pix.height]==sizes[i] and hashlib.sha256(pix.samples).hexdigest()==hashes[i]
            im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
            checked=[(r['page'],fitz.Rect(r['rect'])) for r in regions]
            black &=all(im.crop(box).getbbox() is None for box in pixel_boxes(page,pix,checked,i))
        checks.update(exact_generated_text_in_two_extractors=bool(sequences),text_boxes_aligned=bool(aligned),only_new_text_layer=bool(only_layer),sanitized_image_hashes_match=bool(pixel_hashes),selected_region_pixels_black=bool(black))
        if mode=='best-effort-raster':checks['no_extractable_text']=all(not p.get_text().strip() and not (q.extract_text() or '').strip() for p,q in zip(doc,reader.pages))
        return checks
    finally:doc.close()

def preview(data,page,regions=None,mode='best-effort-raster'):
    if regions is not None:
        payload,_,_=build(data,regions,mode);doc=fitz.open(stream=payload,filetype='pdf')
    else:doc=open_renderable(data)
    try:
        if not 0<=page<len(doc):raise Rejected('Invalid page number.')
        return dict(png=doc[page].get_pixmap(matrix=fitz.Matrix(1,1),colorspace=fitz.csRGB,alpha=False,annots=True).tobytes('png'))
    finally:doc.close()

def prepare_previews(data,regions,options,mode):
    payload,checks,manifest=build(data,regions,mode);doc=fitz.open(stream=payload,filetype='pdf')
    try:pages=[p.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False).tobytes('png') for p in doc]
    finally:doc.close()
    if sum(map(len,pages))>64*1024*1024:raise Rejected('Preview images exceed the local memory limit; export can still be attempted.')
    return dict(pages=pages,checks=checks,cache_key=cache_key(data,regions,options,mode),output_sha256=hashlib.sha256(payload).hexdigest())

def export(data,regions,options,mode,checked=(),expected_output_sha256=None):
    payload,checks,manifest=build(data,regions,mode);digest=hashlib.sha256(payload).hexdigest()
    if expected_output_sha256 is not None and digest!=expected_output_sha256:raise Rejected('Output differs from the current preview; refresh it and try again.')
    report=dict(status='BEST_EFFORT_EXPORTED_INTEGRITY_CHECKS_PASSED_CHECK_CONTENT',mode=mode,input_sha256=hashlib.sha256(data).hexdigest(),output_sha256=digest,pages=len(manifest['records']),redaction_count=len(regions),pages_marked_checked=len(set(checked)),mandatory_review=False,checks=checks,text_diagnostics=manifest['text_diagnostics'],generated_word_counts=[len(w) for w in manifest['records']],skipped_word_counts=manifest['skipped'],known_identifier_count=len(options.get('terms',[])),metadata_scope='Fresh PDF: no source Info/XMP, source IDs, attachments, annotation/form/action objects, bookmarks or prior revisions. Visible annotation/form appearances are flattened into pixels.',content_warning='Unselected visible identifiers can remain. Best-effort selectable text may retain clipped, occluded, mismapped or otherwise hidden source text; absence of hidden identifiers is not verified.' if mode=='best-effort-text' else 'No extractable text layer. Visible identifiers can remain in unselected image pixels. No OCR or automatic anonymity determination.')
    return payload,report
