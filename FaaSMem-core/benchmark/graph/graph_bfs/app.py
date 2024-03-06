import time

import igraph

graph = igraph.Graph.Barabasi(100000, 50)
st = time.time()
graph.bfs(0)
ed = time.time()
print(ed - st)
def handler(handler_context):
    res = graph.bfs(handler_context['id'])
