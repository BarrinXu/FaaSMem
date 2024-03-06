import sys

import requests

sys.path.append('../../')
from config import config

worker_ip = config.WORKERS_IP[0]


def test_to_one(function_name, memory):
    r = requests.get(f'http://{worker_ip}:7998/test',
                     json={'function_name': function_name, 'cold_start_memory': memory})
    res = r.json()
    print(function_name, memory, format(res['duration'], '.3f'))


def test_to_all():
    target_functions = {
        'html_server': [384, 256, 192, 128, 96, 64],
        'graph_bfs': [384, 320, 256, 192, 160, 128],
        'recognizer_adult': [512, 384, 256, 192, 160, 128],
    }
    for function_name in target_functions:
        entry = target_functions[function_name]
        for memory in entry:
            test_to_one(function_name, memory)


test_to_all()
