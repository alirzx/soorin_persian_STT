from soorin_stt.text.persian_normalizer import normalize_text
from soorin_stt.text.security_entities import extract_entities

def test_persian_and_domain_alias():
    norm,entities=normalize_text('مي خواهم  آی پی  192.168.0.1  را  چك كنم',domain='soc')
    assert 'می خواهم' in norm
    assert 'IP 192.168.0.1' in norm
    assert entities[0]['type']=='ipv4'

def test_no_security_alias_general():
    norm,entities=normalize_text('ای دی آر',domain='general')
    assert norm=='ای دی آر' and entities==[]

def test_invalid_ip_excluded():
    assert extract_entities('999.300.2.1')==[]

def test_simple_itn():
    assert normalize_text('پورت هشت',itn=True)[0]=='پورت 8'
