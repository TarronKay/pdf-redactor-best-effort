"""An expanded selection bbox must not be mistaken for redacted-word recovery."""
import fitz
from best_effort_engine import export

def test_adjacent_retained_score_has_expanded_selection_box_without_source_overlap():
 previous=fitz.TOOLS.set_small_glyph_heights()
 try:
  fitz.TOOLS.set_small_glyph_heights(True)
  doc=fitz.open();p=doc.new_page(width=250,height=150)
  p.insert_text((20,40),'Name: SYNTHETIC',fontsize=9)
  p.insert_text((20,52),'Score 83',fontsize=9)
  label=p.get_text('words')[0];box=fitz.Rect(18,label[1]-1,180,label[3]+1)
  selected=[dict(page=0,rect=list(box))]
  assert all(not fitz.Rect(w[:4]).intersects(box) for w in p.get_text('words') if w[4] in {'Score','83'})
  payload,report=export(doc.tobytes(),selected,dict(terms=[]),'best-effort-text',checked=[])
  result=fitz.open(stream=payload,filetype='pdf');page=result[0]
  assert page.get_text().split()==['Score','83'] and all(report['checks'].values())
  assert not any(fitz.Rect(w[:4]).intersects(box) for w in page.get_text('words'))
  fitz.TOOLS.set_small_glyph_heights(False)
  assert any(fitz.Rect(w[:4]).intersects(box) for w in page.get_text('words'))
  result.close();doc.close()
 finally:fitz.TOOLS.set_small_glyph_heights(previous)
