from smriti.pack.packer import Representation,knapsack
def test_bucket_budget():
    groups=[[Representation(str(i),'omit','',0,0),Representation(str(i),'body','x',3,5)] for i in range(3)]
    chosen=knapsack(groups,7,bucket=2)
    assert sum(x.cost for x in chosen)<=7
