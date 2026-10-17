from soorin_stt.text.persian_normalizer import normalize_text

def benchmark_normalize(text):
    return normalize_text(text,domain='general',itn=False)[0]
