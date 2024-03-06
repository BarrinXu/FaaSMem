import numpy as np


def matmul(n):
    A = np.random.rand(n, n)
    B = np.random.rand(n, n)

    C = np.matmul(A, B)


matmul(1000)
