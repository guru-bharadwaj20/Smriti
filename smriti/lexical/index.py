"""Code BM25F with targeted posting updates and cached field statistics."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import json,math
from pathlib import Path
from typing import Any,Mapping
from .tokenizer import code_tokens

@dataclass(frozen=True)
class SearchHit:
    id: str
    score: float

def bm25_score(tf:float,df:int,count:int,length:int,average:float,k1:float=1.2,b:float=0.75)->float:
    if not tf or not average: return 0.0
    idf=math.log(1+(count-df+0.5)/(df+0.5))
    return idf*tf*(k1+1)/(tf+k1*(1-b+b*length/average))

class BM25Index:
    def __init__(self,k1:float=1.2,b:float=0.75,weights:Mapping[str,float]|None=None)->None:
        if not math.isfinite(k1) or k1<=0 or not 0<=b<=1: raise ValueError('invalid BM25 configuration')
        self.k1,self.b=k1,b
        self.weights=dict(weights) if weights is not None else {'signature':3.0,'docstring':2.0,'body':1.0}
        if any(not math.isfinite(w) or w<0 for w in self.weights.values()): raise ValueError('invalid field weights')
        self.documents:dict[str,dict[str,Counter[str]]]={}
        self.postings:dict[str,dict[str,dict[str,int]]]={}
        self._lengths:dict[str,dict[str,int]]={}
        self._totals:dict[str,int]={}
        self._field_documents:dict[str,int]={}

    def add(self,id:str,fields:Mapping[str,str])->None:
        self.remove(id)
        counts={field:Counter(code_tokens(text)) for field,text in fields.items()}
        self.documents[id]=counts
        self._lengths[id]={field:sum(terms.values()) for field,terms in counts.items()}
        for field,terms in counts.items():
            self._field_documents[field]=self._field_documents.get(field,0)+1
            self._totals[field]=self._totals.get(field,0)+self._lengths[id][field]
            for term,count in terms.items(): self.postings.setdefault(term,{}).setdefault(id,{})[field]=count

    def remove(self,id:str)->None:
        fields=self.documents.pop(id,None)
        if fields is None: return
        for field,length in self._lengths.pop(id).items():
            self._totals[field]-=length
            self._field_documents[field]-=1
            if self._field_documents[field]==0:
                del self._totals[field]; del self._field_documents[field]
        for term in {term for terms in fields.values() for term in terms}:
            self.postings[term].pop(id)
            if not self.postings[term]: del self.postings[term]

    @property
    def document_frequency(self)->dict[str,int]: return {term:len(ids) for term,ids in self.postings.items()}
    @property
    def lengths(self)->dict[str,dict[str,int]]: return {id:dict(lengths) for id,lengths in self._lengths.items()}
    @property
    def averages(self)->dict[str,float]: return {field:total/max(1,len(self.documents)) for field,total in self._totals.items()}

    def search(self,query:str,k:int=20)->list[SearchHit]:
        if k<0: raise ValueError('k must be nonnegative')
        scores:dict[str,float]={}; averages=self.averages
        for term in set(code_tokens(query)):
            posting=self.postings.get(term,{})
            idf=math.log(1+(len(self.documents)-len(posting)+0.5)/(len(posting)+0.5))
            for id,fields in posting.items():
                tf=sum(self.weights.get(f,1)*count/(1-self.b+self.b*self._lengths[id][f]/(averages[f] or 1)) for f,count in fields.items())
                if tf: scores[id]=scores.get(id,0)+idf*tf*(self.k1+1)/(tf+self.k1)
        return [SearchHit(id,score) for id,score in sorted(scores.items(),key=lambda item:(-item[1],item[0]))[:k]]

    def save(self,path:str|Path)->None:
        data={'version':1,'k1':self.k1,'b':self.b,'weights':self.weights,'documents':self.documents}
        Path(path).write_text(json.dumps(data,sort_keys=True),encoding='utf-8')

    @classmethod
    def load(cls,path:str|Path)->BM25Index:
        data:dict[str,Any]=json.loads(Path(path).read_text(encoding='utf-8'))
        if data['version']!=1: raise ValueError('unsupported lexical format')
        index=cls(data['k1'],data['b'],data['weights'])
        for id,fields in data['documents'].items():
            counts={field:Counter(terms) for field,terms in fields.items()}
            index.documents[id]=counts
            index._lengths[id]={field:sum(terms.values()) for field,terms in counts.items()}
            for field,terms in counts.items():
                index._field_documents[field]=index._field_documents.get(field,0)+1
                index._totals[field]=index._totals.get(field,0)+index._lengths[id][field]
                for term,count in terms.items(): index.postings.setdefault(term,{}).setdefault(id,{})[field]=count
        return index
