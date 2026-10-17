import re
import unicodedata
from soorin_stt.text.itn import inverse_numbers
from soorin_stt.text.security_entities import replace_known_aliases,extract_entities
TRANSLATE = str.maketrans({'ي':'ی','ك':'ک','ۀ':'ه','ى':'ی','ة':'ه'})

def normalize_text(text:str,domain:str='general',itn:bool=False)->tuple[str,list[dict]]:
    out=unicodedata.normalize('NFKC',text).translate(TRANSLATE)
    out=re.sub(r'\s+',' ',out).strip()
    if itn:
        out=inverse_numbers(out)
    if domain=='soc':
        out=replace_known_aliases(out)
    return out,extract_entities(out) if domain=='soc' else []
