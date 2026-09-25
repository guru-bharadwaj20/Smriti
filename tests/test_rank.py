from smriti.rank.pagerank import personalized_pagerank
from smriti.rank.hybrid import reciprocal_rank_fusion
def test_analytic_stationary_distribution():
    scores=personalized_pagerank({'a':{'b':1},'b':{}},{'a':1},damping=0.5)
    assert abs(scores['a']-2/3)<1e-9
    assert abs(scores['b']-1/3)<1e-9
def test_fusion():
    assert list(reciprocal_rank_fusion([['a','b'],['b','c']],constant=1))[0]=='b'
