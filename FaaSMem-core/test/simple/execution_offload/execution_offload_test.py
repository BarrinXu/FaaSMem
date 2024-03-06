import subprocess
import time


# matmul 47.8M, chameleon 17.2 M, image_processing 68M
functions_memory_list = {
    # 'matmul': [48, 40, 32, 24],
    # 'chameleon_func': [16, 13, 10, 7],
    'image_processing': [60, 50, 40, 30],
               }

for function in functions_memory_list:
    for memory in functions_memory_list[function]:
        command = f'systemd-run --scope -p MemoryMax={memory}M python3 {function}.py'
        lat = []
        print(command)
        for i in range(10):
            st = time.time()
            subprocess.run(command, shell=True)
            ed = time.time()
            lat.append(ed - st)
        print(format(sum(lat) / len(lat), '.3f'))
