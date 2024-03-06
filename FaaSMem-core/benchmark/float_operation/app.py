import math
import time


def float_operations(n):
    start = time.time()
    for i in range(0, n):
        sin_i = math.sin(i)
        cos_i = math.cos(i)
        sqrt_i = math.sqrt(i)
    latency = time.time() - start
    return latency


def handler(handler_context):
    n = int(handler_context['n'])
    result = float_operations(n)
    # print(result)
    # return result
