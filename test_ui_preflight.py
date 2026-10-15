# SPDX-License-Identifier: AGPL-3.0-only
import copy,pytest
from msi_ui_preflight import validate_rows
def sample():
 return ([['Done','370','220','Finish','Finish','Finish']],
 [['Done','Body','Text','20','20','330','130','3',''],['Done','Finish','PushButton','280','180','70','20','3','Finish']],
 [['Done','Finish','EndDialog','Return','1']])
def test_fixed_single_button_cycle():assert validate_rows(*sample())[0]['tab_cycle']==['Finish']
def test_duplicate_predecessor_2810():
 d,c,e=sample();c[0][8]='Finish'
 with pytest.raises(ValueError,match='predecessor count 2'):validate_rows(d,c,e)
def test_dangling_pointer():
 d,c,e=sample();c[1][8]='Missing'
 with pytest.raises(ValueError,match='broken tab edge'):validate_rows(d,c,e)
def test_disconnected_cycles():
 d,c,e=sample();c.append(['Done','Extra','PushButton','20','180','70','20','3','Extra'])
 with pytest.raises(ValueError,match='one closed cycle'):validate_rows(d,c,e)
def test_invalid_first_reference():
 d,c,e=sample();d[0][3]='Missing'
 with pytest.raises(ValueError,match='invalid first reference'):validate_rows(d,c,e)
def test_control_bounds():
 d,c,e=sample();c[1][3]='360'
 with pytest.raises(ValueError,match='bounds'):validate_rows(d,c,e)
def test_invalid_cancel_type():
 d,c,e=sample();d[0][5]='Body'
 with pytest.raises(ValueError,match='push button'):validate_rows(d,c,e)
def test_invalid_event_reference():
 d,c,e=sample();e[0][1]='Missing'
 with pytest.raises(ValueError,match='unknown control'):validate_rows(d,c,e)
