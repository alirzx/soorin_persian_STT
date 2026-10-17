def stable_prefix(previous: str, current: str) -> str:
    """Word-boundary common prefix. Used for optional UI display, not ASR correction."""
    a,b=previous.split(),current.split()
    k=0
    while k<min(len(a),len(b)) and a[k]==b[k]:
        k+=1
    return ' '.join(a[:k])
