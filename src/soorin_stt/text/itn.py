import re
# Conservative rules only: do not hallucinate or reconstruct arbitrary CVE/IP numbers.
_SIMPLE={'صفر':'0','یک':'1','دو':'2','سه':'3','چهار':'4','پنج':'5','شش':'6','هفت':'7','هشت':'8','نه':'9','ده':'10'}
def inverse_numbers(text:str)->str:
    # Only standalone numerals are converted. Larger expressions stay unchanged for safety.
    return re.sub(r'(?<!\w)('+'|'.join(_SIMPLE.keys())+r')(?!\w)',lambda m:_SIMPLE[m.group(0)],text)
