from gevent import monkey

monkey.patch_all()
import random
import sys
import time
import gevent
import numpy as np
import requests

sys.path.append('../../')

from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'

pareto_shape = 0.8
target_range = 50
pre_time = 1 * 60
latencies = []
request_infos = {}
ids = {}
request_interval = 0


def post_request(request_id, function_name):

    while True:
        x = random.paretovariate(pareto_shape)
        if x < target_range + 1:
            target_id = int(x) - 1
            break
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': {'id': target_id}}
    st = time.time()
    r = requests.get(gateway_url.format('run'), json=request_info)
    ed = time.time()
    if st > test_start + pre_time:
        ids[request_id] = {'time': ed - st, 'st': st, 'ed': ed, 'latency': r.json()['latency']}
        latencies.append(r.json()['latency'])
    # print(request_id, ed - st, r.json())


def end_loop(idx, function_name, parallel, duration):
    while time.time() - test_start < pre_time + duration:
        post_request('request_' + str(idx).rjust(4, '0'), function_name)
        time.sleep(request_interval)
        idx += parallel


input_args = ''.join(sys.argv[1:])


def cal_percentile():
    percents = [50, 90, 95, 99]
    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(latencies, percent), '.3f'))


def clean_worker(addr, data):
    r = requests.get(f'http://{addr}:7999/clear', json=data)
    assert r.status_code == 200


def finish_worker(addr):
    r = requests.post(f'http://{addr}:8000/finish')
    assert r.status_code == 200


def test_to_one(function_name, loop_cnt, duration, upd_configs):
    # r = requests.get(f'http://{config.GATEWAY_IP}:7000/upd_configs',
    #                  json={'function_name': function_name, 'upd_configs': {'memory': memory}})
    # assert r.status_code == 200
    # threads_ = []
    # for addr in config.WORKER_ADDRS:
    #     t = threading.Thread(target=clean_worker, args=(addr, ))
    #     threads_.append(t)
    #     t.start()
    # for t in threads_:
    #     t.join()
    for worker_ip in config.WORKERS_IP:
        clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})
    global ids, latencies
    ids = {}
    latencies = []
    # print(f'firing {function_name} with loop {loop_cnt} for {duration} s with {memory}M memory')
    print(f'firing {function_name} with_loop {loop_cnt} for {duration} s')
    print(f'request_interval {request_interval} s {upd_configs}')
    global test_start
    test_start = time.time()
    events = []
    for i in range(loop_cnt):
        events.append(gevent.spawn_later(i * 2, end_loop, i, function_name, loop_cnt, duration))
    for e in events:
        e.join()
    time.sleep(10)

    # threads_ = []
    # for addr in config.WORKER_ADDRS:
    #     t = threading.Thread(target=finish_worker, args=(addr,))
    #     threads_.append(t)
    #     t.start()
    # for t in threads_:
    #     t.join()

    print('total requests count:', len(latencies))
    # get_use_container_log(function_name, loop_cnt, duration)

    print('avg:', format(sum(latencies) / len(latencies), '.3f'))
    cal_percentile()


def test_to_all():
    print(input_args)
    default_configs = {'video_ffmpeg': {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.5},
                       'html_server': {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': False, 'cpu': 0.1}}
    target_functions = {
        # 'recognizer_adult': [
        #     {'loop': 1, 'duration': 2, 'configs': {'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 4, 'duration': 2, 'configs': {'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.5}},
        #     {'loop': 16, 'duration': 2, 'configs': {'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.5}},
        # ],
        'html_server': [
            {'loop': 4, 'duration': 300, 'configs': {'exec_memory': 512, 'idle_memory': 512, 'exec_tuning': True, 'cpu': 0.2}},
            {'loop': 1, 'duration': 3, 'configs': {'exec_memory': 384, 'idle_memory': 384, 'exec_tuning': False, 'cpu': 0.1}},
            {'loop': 1, 'duration': 3, 'configs': {'exec_memory': 256, 'idle_memory': 256, 'exec_tuning': False, 'cpu': 0.1}},
            {'loop': 1, 'duration': 3, 'configs': {'exec_memory': 192, 'idle_memory': 192, 'exec_tuning': False, 'cpu': 0.1}},
            {'loop': 1, 'duration': 3, 'configs': {'exec_memory': 128, 'idle_memory': 128, 'exec_tuning': False, 'cpu': 0.1}},
            {'loop': 1, 'duration': 3, 'configs': {'exec_memory': 64, 'idle_memory': 64, 'exec_tuning': False, 'cpu': 0.1}},
        ],
    }
    for function_name in target_functions:
        for entry in target_functions[function_name]:
            test_to_one(function_name, entry['loop'], 60 * entry['duration'], entry['configs'])


test_to_all()
