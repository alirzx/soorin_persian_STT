import re
ALIASES={'ای دی آر':'EDR','اس آی ای ام':'SIEM','آی پی':'IP','سی وی ای':'CVE',
         'پاورشل':'PowerShell','ویندوز':'Windows'}
PATTERNS={
    'cve':re.compile(r'\bCVE-\d{4}-\d{4,}\b',re.I),
    'ipv4':re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'domain':re.compile(r'\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b'),
}
def replace_known_aliases(text:str)->str:
    for name,replacement in ALIASES.items():
        text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',replacement,text)
    return text

def extract_entities(text:str)->list[dict]:
    entities=[]
    for kind,pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            value=match.group()
            if kind=='ipv4' and not all(int(x)<=255 for x in value.split('.')):
                continue
            entities.append({'type':kind,'raw':value,'normalized':value,'start':match.start(),'end':match.end()})
    return sorted(entities,key=lambda e:e['start'])
