import random

pareto_shape = 0.5
target_range = 50

a = []
count = []
for i in range(100000):
    a.append(random.paretovariate(0.1))
for i in range(100000):
    count.append(0)
print(a)


for x in a:
    if x < 100001:
        index = int(x) - 1
        count[index] += 1
print(count)
