import numpy as np

def levenshtein(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nr=[i]
        for j,y in enumerate(b,1):
            nr.append(min(nr[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nr
    return row[-1]

def wer(ref,hyp):
    r=ref.split();h=hyp.split()
    return levenshtein(r,h)/max(1,len(r))

def cer(ref,hyp):
    return levenshtein(list(ref),list(hyp))/max(1,len(ref))
