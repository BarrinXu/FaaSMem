import numpy as np
import time


def matmul(n):
    A = np.random.rand(n, n)
    B = np.random.rand(n, n)

    start = time.time()
    C = np.matmul(A, B)
    latency = time.time() - start
    return latency


def handler(handler_context):
    n = int(handler_context['n'])
    result = matmul(n)
    # print(result)
    # return result
