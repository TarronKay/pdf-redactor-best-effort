import fitz,pytest
from best_effort_engine import analyze,export
from identifier_matching import folded_identifier_rects

def document():
    doc=fitz.open();p=doc.new_page()
    for y,text in [(60,'Alice ALICE alice'),(90,'Jörg JÖRG jörg'),(120,'Straße STRASSE strasse'),(150,'Elodie Élodie')]:p.insert_text((40,y),text,fontname='helv')
    return doc

@pytest.mark.parametrize('term,count',[('aLiCe',3),('jÖrG',3),('STRASSE',3),('élodie',1)])
def test_casefold_suggestions_cover_every_literal_variant(term,count):
    doc=document();p=doc[0];matches=folded_identifier_rects(p,[term]);assert len(matches)==count
    raw=doc.tobytes();info=analyze(raw,terms=[term])
    payload,report=export(raw,info['regions'],dict(terms=[term]),'best-effort-text',checked=[])
    result=fitz.open(stream=payload,filetype='pdf')
    assert term.casefold() not in result[0].get_text().casefold()
    assert all(report['checks'].values());result.close()
    doc.close()

def test_casefold_expansion_rect_covers_whole_original_glyph():
    doc=document();p=doc[0];rect=folded_identifier_rects(p,['STRASSE'])[0]
    assert rect.contains(p.search_for('Straße')[0])
    doc.close()

def test_accents_are_not_removed_and_metacharacters_are_literal():
    doc=document();assert len(folded_identifier_rects(doc[0],['Elodie']))==1
    assert not folded_identifier_rects(doc[0],['J.*g'])
    doc.close()

def test_old_crossline_search_still_contributes():
    doc=fitz.open();p=doc.new_page();p.insert_text((40,60),'Confiden-');p.insert_text((40,75),'tial Identifier')
    p.insert_text((40,100),'Other educational words for analysis')
    expected=p.search_for('Confiden- tial');assert expected
    info=analyze(doc.tobytes(),terms=['Confiden- tial'])
    assert all(any(fitz.Rect(r['rect']).contains(box) for r in info['regions']) for box in expected)
    doc.close()

def test_multiple_pages_match_without_cross_page_deduplication():
    doc=document();doc.new_page().insert_text((40,60),'JÖRG')
    info=analyze(doc.tobytes(),terms=['jörg'])
    assert {r['page'] for r in info['regions'] if r['reason']=='user-supplied term'}=={0,1}
    doc.close()
