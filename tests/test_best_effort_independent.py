"""Independent generic rebuild and actual-thread UI checks; never opens Tk."""
import base64
import hashlib
import io
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import fitz
import pytest
from pypdf import PdfReader
from PIL import Image, ImageDraw
import best_effort_engine as engine
import best_effort_app as module
from tests.ui_fakes import (Var,Frame,Label,Button,Checkbutton,
    Radiobutton,Scrollbar,Text,Canvas,Root,load,finish,visible)


def specimen():
    doc=fitz.open();p=doc.new_page(width=320,height=240)
    p.insert_text((20,30),'PUBLIC SECRETSELECTED',fontsize=11)
    p.insert_text((20,65),'WHITEHIDDEN',fontsize=11,color=(1,1,1))
    p.insert_text((20,95),'COVEREDHIDDEN',fontsize=11)
    p.draw_rect(fitz.Rect(10,75,180,100),color=None,fill=(1,1,1))
    p.insert_text((20,125),'INVISIBLEPAINTER',fontsize=11,render_mode=3)
    a=p.add_freetext_annot(fitz.Rect(20,140,200,165),'ANNOTVISIBLE',fontsize=11)
    a.set_info(title='PRIVATEANNOTAUTHOR',content='ANNOTVISIBLE');a.update()
    widget=fitz.Widget();widget.field_name='PRIVATEFIELD';widget.field_type=fitz.PDF_WIDGET_TYPE_TEXT
    widget.field_value='FORMVISIBLE';widget.rect=fitz.Rect(20,175,200,198);widget.text_fontsize=11
    p.add_widget(widget)
    p.insert_link({'kind':fitz.LINK_URI,'from':fitz.Rect(20,20,60,35),'uri':'https://private.invalid/PRIVATEURI'})
    doc.set_metadata(dict(title='PRIVATETITLE',author='PRIVATEAUTHOR',subject='PRIVATESUBJECT',keywords='PRIVATEKEYWORD'))
    doc.set_xml_metadata('<private>PRIVATEXMP</private>')
    doc.embfile_add('PRIVATEATTACHMENT',b'PRIVATEATTACHMENTDATA')
    doc.set_toc([[1,'PRIVATEBOOKMARK',1]])
    doc.xref_set_key(doc.pdf_catalog(),'OpenAction','<< /S /JavaScript /JS (PRIVATEACTION) >>')
    doc.new_page(width=170,height=110) # no fonts or text, arbitrary unrecognized layout
    payload=doc.tobytes();doc.close();return payload


@pytest.mark.parametrize('mode',sorted(engine.MODES))
def test_generic_rebuild_metadata_annotations_pixels_and_zero_word_page(mode):
    source=specimen();original_hash=hashlib.sha256(source).hexdigest()
    doc=fitz.open(stream=source,filetype='pdf');word=next(w for w in doc[0].get_text('words') if w[4]=='SECRETSELECTED')
    region=dict(page=0,rect=[word[0]+1.15,word[1]+.25,word[0]+2.1,word[3]-.25])
    expected=[]
    for i,p in enumerate(doc):
        pix=p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False,annots=True)
        image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        if i==0:
            import math
            r=region['rect'];box=(math.floor(r[0]*2),math.floor(r[1]*2),math.ceil(r[2]*2),math.ceil(r[3]*2))
            ImageDraw.Draw(image).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill='black')
        expected.append(image.tobytes())
    # Verify fixture really contains visible annotation / form appearances.
    assert doc[0].get_pixmap(annots=True).samples!=doc[0].get_pixmap(annots=False).samples
    doc.close()
    payload,report=engine.export(source,[region],dict(terms=['PRIVATEKNOWNTERM']),mode,checked=[])
    assert all(report['checks'].values()) and report['mandatory_review'] is False
    assert report['pages_marked_checked']==0 and report['known_identifier_count']==1
    assert hashlib.sha256(source).hexdigest()==original_hash
    reader=PdfReader(io.BytesIO(payload),strict=True)
    assert set(reader.trailer['/Root'])=={'/Type','/Pages'}
    assert '/Info' not in reader.trailer and '/ID' not in reader.trailer
    out=fitz.open(stream=payload,filetype='pdf')
    decoded=b'\n'.join(out.xref_stream(i) or b'' for i in range(1,out.xref_length()))
    objects='\n'.join(out.xref_object(i) for i in range(1,out.xref_length())).encode()
    for secret in ['PRIVATETITLE','PRIVATEAUTHOR','PRIVATESUBJECT','PRIVATEKEYWORD','PRIVATEXMP','PRIVATEATTACHMENT','PRIVATEBOOKMARK','PRIVATEACTION','PRIVATEFIELD','PRIVATEANNOTAUTHOR','PRIVATEURI','PRIVATEKNOWNTERM']:
        assert secret.encode() not in payload+decoded+objects+json.dumps(report).encode()
    for i,p in enumerate(out):
        pix=fitz.Pixmap(out,p.get_images()[0][0]);assert pix.samples==expected[i]
        assert p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False).samples==expected[i]
        assert not list(p.annots() or []) and not list(p.widgets() or []) and not p.get_links()
    text=out[0].get_text();other=reader.pages[0].extract_text() or ''
    assert text.split()==other.split()
    assert 'SECRETSELECTED' not in text and 'INVISIBLEPAINTER' not in text
    if mode.endswith('text'):
        assert 'PUBLIC' in text
        # This deliberate residual distinguishes best-effort from a visibility proof.
        assert 'WHITEHIDDEN' in text and 'COVEREDHIDDEN' in text
        assert 'hidden' in report['content_warning'] and 'not verified' in report['content_warning']
    else:assert not text.strip() and not other.strip()
    assert not out[1].get_text().strip();out.close()


def test_empty_selection_unrecognized_layout_needs_no_review():
    raw=specimen();info=engine.analyze(raw,False,False,())
    assert info['blockers']==[]
    payload,report=engine.export(raw,[],{},'best-effort-text')
    assert report['redaction_count']==0 and report['pages_marked_checked']==0
    assert all(report['checks'].values())
    assert 'SECRETSELECTED' in fitz.open(stream=payload,filetype='pdf')[0].get_text()


def test_integrity_rejects_extra_unreachable_object_and_page_transform():
    payload,checks,m=engine.build(specimen(),[],'best-effort-text')
    for mutation in ['unreachable','transform']:
        doc=fitz.open(stream=payload,filetype='pdf')
        if mutation=='unreachable':
            x=doc.get_new_xref();doc.update_object(x,'<< /Private (DO_NOT_COPY) >>')
        else:
            p=doc[0];x=p.get_contents()[0];doc.update_stream(x,b'0.5 0 0 0.5 0 0 cm\n'+doc.xref_stream(x))
        changed=doc.tobytes(no_new_id=True);doc.close()
        result=engine.verify(changed,m['records'],m['hashes'],m['sizes'],[],'best-effort-text')
        assert not result['fresh_allowlisted_objects']


@pytest.mark.parametrize('region',[dict(page=-1,rect=[1,2,3,4]),dict(page=0,rect=[-1,1,3,4]),dict(page=0,rect=[1,1,1,4]),dict(page=0,rect=[1,float('nan'),3,4])])
def test_invalid_selected_boxes_still_fail_closed(region):
    with pytest.raises(engine.Rejected):engine.build(specimen(),[region],'best-effort-raster')


def test_password_and_oversize_input_still_rejected():
    with pytest.raises(engine.Rejected):engine.open_renderable(b'x'*(engine.MAX_BYTES+1))
    doc=fitz.open();doc.new_page();raw=doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,user_pw='secret',owner_pw='owner');doc.close()
    with pytest.raises(engine.Rejected):engine.open_renderable(raw)


@pytest.mark.parametrize('rotation',[90,180,270])
def test_rotated_cropped_page_pixels_and_display_coordinate_redaction(rotation):
    import math
    doc=fitz.open();p=doc.new_page(width=350,height=260)
    p.insert_text((70,80),'ROTATEDSECRET',fontsize=11)
    p.draw_rect(fitz.Rect(65,100,120,140),color=None,fill=(1,0,0))
    p.set_cropbox(fitz.Rect(40,30,300,230));p.set_rotation(rotation)
    raw=doc.tobytes();doc.close();doc=fitz.open(stream=raw,filetype='pdf');p=doc[0]
    r=fitz.Rect(p.get_text('words')[0][:4])*p.rotation_matrix
    region=dict(page=0,rect=list(r))
    pix=p.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False,annots=True)
    expected=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
    box=(math.floor(r.x0*2),math.floor(r.y0*2),math.ceil(r.x1*2),math.ceil(r.y1*2))
    ImageDraw.Draw(expected).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill='black')
    dimensions=tuple(p.rect);doc.close()
    info=engine.analyze(raw,False,False,('ROTATEDSECRET',))
    assert (info['pages'][0]['width'],info['pages'][0]['height'])==(dimensions[2],dimensions[3])
    assert any(fitz.Rect(x['rect']).intersects(r) for x in info['regions'])
    payload,checks,_=engine.build(raw,[region],'best-effort-text')
    out=fitz.open(stream=payload,filetype='pdf')
    assert all(checks.values()) and tuple(out[0].rect)==dimensions
    assert out[0].get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csRGB,alpha=False).samples==expected.tobytes()
    assert 'ROTATEDSECRET' not in out[0].get_text();out.close()


@pytest.fixture
def app(monkeypatch):
    for name,klass in [('Frame',Frame),('Label',Label),('Button',Button),('Checkbutton',Checkbutton),('Radiobutton',Radiobutton),('Scrollbar',Scrollbar)]:monkeypatch.setattr(module.ttk,name,klass)
    for name,klass in [('BooleanVar',Var),('StringVar',Var),('Text',Text),('Canvas',Canvas)]:monkeypatch.setattr(module.tk,name,klass)
    monkeypatch.setattr(module.messagebox,'showerror',lambda *a,**k:pytest.fail('unexpected dialog'))
    return module.BestEffortApp(Root())


def test_actual_constructor_optional_review_and_unreviewed_navigation(app):
    assert app.selectable.get() and app.final.get()
    assert 'BestEffortApp(root)' in Path(module.__file__).with_name('release_gui.py').read_text()
    assert 'hidden/occluded' in app.mode_status.get()
    assert visible(app.buttons[5]) and app.buttons[5].cget('text')=='Mark checked (optional)'
    load(app);assert app._can_export() and not app.reviewed
    app.show=lambda:None;app.buttons[3].invoke()
    assert app.page==1 and not app.reviewed and app._can_export()
    assert app.buttons[3].cget('text')=='Last page'
    app._pending=True;app._update_controls();assert not app._can_export()
    assert app.buttons[6].cget('state')=='disabled'


def test_refresh_never_drops_any_selected_suggestion_or_manual_box(app):
    load(app);app.show=lambda:None
    old=[dict(page=0,rect=[1,2,5,6],reason='automatic'),dict(page=1,rect=[10,20,30,40],reason='manual')]
    app.regions=old.copy();app.request_refresh()
    result=dict(app.info,regions=[dict(old[0]),dict(page=0,rect=[40,50,60,70],reason='new')])
    app._refresh_done(result,app._generation,app._analysis_key())
    assert app.regions==old+[result['regions'][1]] and not app._pending
    app.request_refresh();newest=list(app.regions)
    app._refresh_done(dict(result,regions=[]),app._generation-1,app._analysis_key())
    assert app.regions==newest and app._pending


def test_real_export_without_cache_or_reviews_and_stale_completion(app,monkeypatch):
    load(app);requests=[];writes=[];started=threading.Event();release=threading.Event()
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **k:'not-written.pdf')
    monkeypatch.setattr(module,'write_new_pair',lambda *a,**k:writes.append(a) or SimpleNamespace(pdf_path=Path('out.pdf'),report_path=Path('out.json')))
    def worker(data,op,**kwargs):
        requests.append((data,op,kwargs));started.set();assert release.wait(3)
        return dict(pdf=base64.b64encode(b'test').decode(),report={})
    monkeypatch.setattr(module,'call_best_effort_worker',worker)
    app.export();assert started.wait(3);release.set();finish(app)
    assert len(writes)==1 and requests[0][2]['checked']==[] and requests[0][2]['expected_output_sha256'] is None
    started.clear();release.clear();app.export();assert started.wait(3)
    app.terms.value='new identifier';app.identifiers_changed();release.set();finish(app)
    assert len(writes)==1 and app._pending and 'nothing was saved' in app.status.get()


def test_preview_failure_does_not_impose_review_gate_and_thread_failure_recovers(app,monkeypatch):
    load(app)
    monkeypatch.setattr(module,'call_best_effort_worker',lambda *a,**k:(_ for _ in ()).throw(OSError('synthetic preview failure')))
    app.show();finish(app)
    assert 'Preview unavailable' in app.status.get() and app._can_export() and not app._can_review()
    app.run(lambda:(_ for _ in ()).throw(OSError('synthetic operation error')),lambda value:pytest.fail('failure called success'))
    finish(app)
    assert not app.busy and app._can_export() and 'synthetic operation error' in app.status.get()


def test_unannounced_geometry_change_during_export_is_not_written(app,monkeypatch):
    load(app);started=threading.Event();release=threading.Event()
    app.regions=[dict(page=0,rect=[1,2,5,6],reason='selected')]
    monkeypatch.setattr(module.filedialog,'asksaveasfilename',lambda **k:'not-written.pdf')
    def worker(*args,**kwargs):
        started.set();assert release.wait(3)
        return dict(pdf='dGVzdA==',report={})
    monkeypatch.setattr(module,'call_best_effort_worker',worker)
    monkeypatch.setattr(module,'write_new_pair',lambda *a,**k:pytest.fail('changed selected geometry saved'))
    app.export();assert started.wait(3)
    app.regions[0]['rect'][2]=15 # deliberately bypass invalidate; state hash must catch it
    release.set();finish(app)
    assert 'nothing was saved' in app.status.get()


def test_actual_isolated_worker_accepts_no_review_no_template():
    from best_effort_controller import call_best_effort_worker
    source=specimen()
    for mode in sorted(engine.MODES):
        response=call_best_effort_worker(source,'export',regions=[],options={},mode=mode,checked=[])
        output=base64.b64decode(response['pdf'],validate=True)
        assert hashlib.sha256(output).hexdigest()==response['report']['output_sha256']
        assert all(response['report']['checks'].values())
        assert response['report']['mandatory_review'] is False
