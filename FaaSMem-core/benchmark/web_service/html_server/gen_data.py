
with open('data/0.mhtml', 'r') as f:
    content = f.read()

for i in range(1, 50):
    with open(f'data/{i}.mhtml', 'w') as f:
        f.write(content)
