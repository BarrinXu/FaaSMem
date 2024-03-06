from gevent import monkey

monkey.patch_all()
import random
import json
import os
import sys
import time
import gevent
from tqdm import tqdm
import numpy as np
import requests
import datetime

sys.path.append('../../')
sys.path.append('../../../')

from common_lib import make_handler_context
from common_lib import ops
from config import config

gateway_url = 'http://' + config.GATEWAY_URL + '/{}'


latencies = []
requests_pgmjfault = []
firing_timestamps = []
request_infos = {}
ids = {}
input_args = ''.join(sys.argv[1:])
with open('../../../trace/trace_tidy.json', 'r') as f:
    raw_trace = json.load(f)


def post_request(request_id, function_name):
    request_info = {'request_id': request_id,
                    'function_name': function_name,
                    'runtime_configs': {},
                    'handler_context': make_handler_context.make_context(function_name)}
    st = time.time()
    r = requests.get(gateway_url.format('run'), json=request_info)
    ed = time.time()
    ids[request_id] = {'time': ed - st, 'st': st, 'ed': ed, 'latency': r.json()['latency']}
    latencies.append(r.json()['latency'])
    requests_pgmjfault.append(r.json()['pgmjfault'])
    firing_timestamps.append(st)
    # print(request_id, ed - st, r.json())


def analysis_for_container_recall(start_timestamps, exec_duration, keep_alive=600):
    print('total request in now time window:', len(start_timestamps))
    end_timestamps = []
    container_idle_times = []
    idle_containers = []
    for time_stamp in start_timestamps:
        while len(end_timestamps) > 0 and end_timestamps[0] < time_stamp:
            idle_containers.append(end_timestamps.pop(0))
        if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > time_stamp:
            container_idle_times.append(time_stamp - idle_containers.pop(-1))
        # else:
        #     container_idle_times.append(keep_alive)
        end_timestamps.append(time_stamp + exec_duration)
    container_idle_times.sort()
    # print(len(container_idle_times))
    # print(container_idle_times)
    return ops.cal_percentile(container_idle_times, percentile_number=99)


def test_to_one(function_name, trace_id, start_idx, exp_duration, upd_configs):
    global ids, latencies, firing_timestamps, requests_pgmjfault
    ids = {}
    latencies = []
    firing_timestamps = []
    requests_pgmjfault = []
    print(f'firing {function_name} with_trace {trace_id}-{start_idx} with {exp_duration} s and {upd_configs}')

    incoming_timestamps = raw_trace['per_function_invocations'][trace_id]['incoming_timestamps'][start_idx:]
    print(f'total request in trace: {len(incoming_timestamps)}')

    start_timestamp = incoming_timestamps[0] - 1
    last_timestamp = incoming_timestamps[0] + exp_duration

    exec_duration = upd_configs['exec_duration'] * 1.2
    for i, time_stamp in enumerate(incoming_timestamps):
        if time_stamp > last_timestamp:
            incoming_timestamps = incoming_timestamps[:i]
            break

    print('---analysis for container reuse interval start---')
    semiwarm_delay = analysis_for_container_recall(incoming_timestamps, exec_duration=exec_duration)
    print('semiwarm_delay_ideal:', semiwarm_delay)
    semiwarm_delay = max(semiwarm_delay, 59)
    print('semiwarm_delay_real:', semiwarm_delay)
    upd_configs['semiwarm_delay'] = int(semiwarm_delay + 1)

    print('---analysis for container reuse interval end---')

    for worker_ip in config.WORKERS_IP:
        ops.clean_worker(worker_ip, {'upd_configs': {function_name: upd_configs}})


    # for i in range(len(incoming_timestamps) - exp_cnt - 10):
    #     if incoming_timestamps[i + exp_cnt - 1] - incoming_timestamps[i] < 20000:
    #         incoming_timestamps = incoming_timestamps[i:]
    #         break

    for worker_ip in config.WORKERS_IP:
        ops.start_monitor(worker_ip)

    start_local_time = time.time()

    # print(f'testing duration: {last_timestamp - start_timestamp} s')

    request_idx = 0
    for time_stamp in tqdm(incoming_timestamps):
        if time_stamp > last_timestamp:
            break
        gevent.sleep(max(0, time_stamp - (start_timestamp + time.time() - start_local_time)))
        gevent.spawn(post_request, 'request_' + str(request_idx).rjust(5, '0'), function_name)
        request_idx += 1
        # if request_idx == exp_cnt:
        #     break
    gevent.sleep(max(0, last_timestamp - (start_timestamp + time.time() - start_local_time)))
    gevent.sleep(15)

    monitor_logs = None

    for worker_ip in config.WORKERS_IP:
        monitor_logs = ops.end_monitor(worker_ip)
    assert monitor_logs is not None
    time.sleep(5)

    print('total requests count:', len(latencies))
    # get_use_container_log(function_name, loop_cnt, duration)

    print('avg:', format(sum(latencies) / len(latencies), '.3f'))
    ops.cal_percentile(latencies)

    nowtime = str(datetime.datetime.now())
    nowtime = nowtime.replace(':', '_')
    system_tag = ''
    if 'semiwarm' in upd_configs and upd_configs['semiwarm'] is False:
        system_tag = '-no-semiwarm'
    if 'MGLRU' in upd_configs and upd_configs['MGLRU'] is False:
        system_tag = '-no-MGLRU'
    if not os.path.exists('result'):
        os.mkdir('result')
    suffix = (f'AzureTraceLatency_'
              f'{function_name}_{trace_id}_{start_idx}_{exp_duration}_'
              f'({upd_configs["system"]}{system_tag})')

    filepath = os.path.join('result', nowtime + '_' + suffix + '.json')

    with open(filepath.replace('AzureTraceLatency', 'AzureTraceGlobalmonitor'), 'w') as f:
        json.dump(monitor_logs, f)

    save_logs = {'configs': upd_configs, 'function_name': function_name, 'trace_id': trace_id, 'start_idx': start_idx,
                 'exp_duration': exp_duration, 'args': input_args,
                 'latencies': latencies, 'firing_timestamps': firing_timestamps,
                 'requests_pgmjfault': requests_pgmjfault}
    with open(filepath, 'w') as f:
        json.dump(save_logs, f)


def test_to_all():
    general_tests = {
        0: {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 3600},
        '0-sp1': {'trace_id': 0, 'start_idx': 13958, 'exp_duration': 3600},
        '0-sp2': {'trace_id': 0, 'start_idx': 29277, 'exp_duration': 3600},
        '0-sp3': {'trace_id': 0, 'start_idx': 39348, 'exp_duration': 3600},
        '0-debug': {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 60},
        '0-ablation': {'trace_id': 0, 'start_idx': 8967, 'exp_duration': 3600 * 8},
        '3-ablation': {'trace_id': 3, 'start_idx': 52391, 'exp_duration': 3600 * 8},
        '2-ablation': {'trace_id': 2, 'start_idx': 18320, 'exp_duration': 3600 * 8},
        2: {'trace_id': 2, 'start_idx': 502, 'exp_duration': 3600},
        '2-debug': {'trace_id': 2, 'start_idx': 502, 'exp_duration': 60},

        3: {'trace_id': 3, 'start_idx': 27267, 'exp_duration': 3600},
        '3-sp1': {'trace_id': 3, 'start_idx': 0, 'exp_duration': 3600},
        4: {'trace_id': 4, 'start_idx': 0, 'exp_duration': 3600},
        5: {'trace_id': 5, 'start_idx': 6168, 'exp_duration': 3600},
        6: {'trace_id': 6, 'start_idx': 35316, 'exp_duration': 3600},
        7: {'trace_id': 7, 'start_idx': 42167, 'exp_duration': 3600},
        8: {'trace_id': 8, 'start_idx': 52, 'exp_duration': 3600},
        9: {'trace_id': 9, 'start_idx': 0, 'exp_duration': 3600},
        10: {'trace_id': 10, 'start_idx': 0, 'exp_duration': 3600},
        11: {'trace_id': 11, 'start_idx': 16, 'exp_duration': 3600},
        12: {'trace_id': 12, 'start_idx': 0, 'exp_duration': 3600},
        17: {'trace_id': 17, 'start_idx': 0, 'exp_duration': 3600},

        14: {'trace_id': 14, 'start_idx': 2009, 'exp_duration': 3600},
        '14-sp1': {'trace_id': 14, 'start_idx': 2370, 'exp_duration': 3600},
        15: {'trace_id': 15, 'start_idx': 4003, 'exp_duration': 3600},
        16: {'trace_id': 16, 'start_idx': 3000, 'exp_duration': 3600},
        '16-sp1': {'trace_id': 16, 'start_idx': 3100, 'exp_duration': 3600},
        25: {'trace_id': 25, 'start_idx': 5017, 'exp_duration': 3600},

        60: {'trace_id': 60, 'start_idx': 0, 'exp_duration': 3600},

        86: {'trace_id': 86, 'start_idx': 0, 'exp_duration': 3600}, # Especially for DAMON

    }
    target_functions = {

        'graph_bfs': {'configs': {'raw_memory': 885, 'cpu': 0.5, 'exec_duration': 0.3}, 'tests': [


            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},

            # {'test_id': 0, 'configs': {'system': 'baseline'}},
            # {'test_id': 0, 'configs': {'system': 'TMO'}},
            # {'test_id': 0, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 3, 'configs': {'system': 'baseline'}},
            # {'test_id': 3, 'configs': {'system': 'TMO'}},
            # {'test_id': 3, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 4, 'configs': {'system': 'baseline'}},
            # {'test_id': 4, 'configs': {'system': 'TMO'}},
            # {'test_id': 4, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 5, 'configs': {'system': 'baseline'}},
            # {'test_id': 5, 'configs': {'system': 'TMO'}},
            # {'test_id': 5, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 6, 'configs': {'system': 'baseline'}},
            # {'test_id': 6, 'configs': {'system': 'TMO'}},
            # {'test_id': 6, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 7, 'configs': {'system': 'baseline'}},
            # {'test_id': 7, 'configs': {'system': 'TMO'}},
            # {'test_id': 7, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 8, 'configs': {'system': 'baseline'}},
            # {'test_id': 8, 'configs': {'system': 'TMO'}},
            # {'test_id': 8, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 9, 'configs': {'system': 'baseline'}},
            # {'test_id': 9, 'configs': {'system': 'TMO'}},
            # {'test_id': 9, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 10, 'configs': {'system': 'baseline'}},
            # {'test_id': 10, 'configs': {'system': 'TMO'}},
            # {'test_id': 10, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 11, 'configs': {'system': 'baseline'}},
            # {'test_id': 11, 'configs': {'system': 'TMO'}},
            # {'test_id': 11, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 12, 'configs': {'system': 'baseline'}},
            # {'test_id': 12, 'configs': {'system': 'TMO'}},
            # {'test_id': 12, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 17, 'configs': {'system': 'baseline'}},
            # {'test_id': 17, 'configs': {'system': 'TMO'}},
            # {'test_id': 17, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 14, 'configs': {'system': 'baseline'}},
            # {'test_id': 14, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 15, 'configs': {'system': 'baseline'}},
            # {'test_id': 15, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 16, 'configs': {'system': 'baseline'}},
            # {'test_id': 16, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 25, 'configs': {'system': 'baseline'}},
            # {'test_id': 25, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '14-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '14-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '16-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '16-sp1', 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '0-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp2', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp2', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp3', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp3', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '3-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '3-sp1', 'configs': {'system': 'FaaSMem'}},
        ]},
        'bert': {'configs': {'raw_memory': 1770, 'cpu': 1, 'exec_duration': 0.15}, 'tests': [

            {'test_id': '3-ablation', 'configs': {'system': 'baseline'}},
            {'test_id': '3-ablation', 'configs': {'system': 'FaaSMem'}},
            {'test_id': '3-ablation', 'configs': {'system': 'FaaSMem', 'MGLRU': False}},
            {'test_id': '3-ablation', 'configs': {'system': 'FaaSMem', 'semiwarm': False}},

            {'test_id': '0-ablation', 'configs': {'system': 'baseline'}},
            {'test_id': '0-ablation', 'configs': {'system': 'FaaSMem'}},
            {'test_id': '0-ablation', 'configs': {'system': 'FaaSMem', 'MGLRU': False}},
            {'test_id': '0-ablation', 'configs': {'system': 'FaaSMem', 'semiwarm': False}},

            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},

            # {'test_id': '0-debug', 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 0, 'configs': {'system': 'baseline'}},
            # {'test_id': 0, 'configs': {'system': 'TMO'}},
            # {'test_id': 0, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 3, 'configs': {'system': 'baseline'}},
            # {'test_id': 3, 'configs': {'system': 'TMO'}},
            # {'test_id': 3, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 4, 'configs': {'system': 'baseline'}},
            # {'test_id': 4, 'configs': {'system': 'TMO'}},
            # {'test_id': 4, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 5, 'configs': {'system': 'baseline'}},
            # {'test_id': 5, 'configs': {'system': 'TMO'}},
            # {'test_id': 5, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 6, 'configs': {'system': 'baseline'}},
            # {'test_id': 6, 'configs': {'system': 'TMO'}},
            # {'test_id': 6, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 7, 'configs': {'system': 'baseline'}},
            # {'test_id': 7, 'configs': {'system': 'TMO'}},
            # {'test_id': 7, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 8, 'configs': {'system': 'baseline'}},
            # {'test_id': 8, 'configs': {'system': 'TMO'}},
            # {'test_id': 8, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 9, 'configs': {'system': 'baseline'}},
            # {'test_id': 9, 'configs': {'system': 'TMO'}},
            # {'test_id': 9, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 10, 'configs': {'system': 'baseline'}},
            # {'test_id': 10, 'configs': {'system': 'TMO'}},
            # {'test_id': 10, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 11, 'configs': {'system': 'baseline'}},
            # {'test_id': 11, 'configs': {'system': 'TMO'}},
            # {'test_id': 11, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 12, 'configs': {'system': 'baseline'}},
            # {'test_id': 12, 'configs': {'system': 'TMO'}},
            # {'test_id': 12, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 17, 'configs': {'system': 'baseline'}},
            # {'test_id': 17, 'configs': {'system': 'TMO'}},
            # {'test_id': 17, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 14, 'configs': {'system': 'baseline'}},
            # {'test_id': 14, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 15, 'configs': {'system': 'baseline'}},
            # {'test_id': 15, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 16, 'configs': {'system': 'baseline'}},
            # {'test_id': 16, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 25, 'configs': {'system': 'baseline'}},
            # {'test_id': 25, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '14-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '14-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '16-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '16-sp1', 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '0-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp2', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp2', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp3', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp3', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '3-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '3-sp1', 'configs': {'system': 'FaaSMem'}},
        ]},
        'html_server': {'configs': {'raw_memory': 354, 'cpu': 0.2, 'exec_duration': 0.15}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},

            # {'test_id': 0, 'configs': {'system': 'baseline'}},
            # {'test_id': 0, 'configs': {'system': 'TMO'}},
            # {'test_id': 0, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 3, 'configs': {'system': 'baseline'}},
            # {'test_id': 3, 'configs': {'system': 'TMO'}},
            # {'test_id': 3, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 4, 'configs': {'system': 'baseline'}},
            # {'test_id': 4, 'configs': {'system': 'TMO'}},
            # {'test_id': 4, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 5, 'configs': {'system': 'baseline'}},
            # {'test_id': 5, 'configs': {'system': 'TMO'}},
            # {'test_id': 5, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 6, 'configs': {'system': 'baseline'}},
            # {'test_id': 6, 'configs': {'system': 'TMO'}},
            # {'test_id': 6, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 7, 'configs': {'system': 'baseline'}},
            # {'test_id': 7, 'configs': {'system': 'TMO'}},
            # {'test_id': 7, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 8, 'configs': {'system': 'baseline'}},
            # {'test_id': 8, 'configs': {'system': 'TMO'}},
            # {'test_id': 8, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 9, 'configs': {'system': 'baseline'}},
            # {'test_id': 9, 'configs': {'system': 'TMO'}},
            # {'test_id': 9, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 10, 'configs': {'system': 'baseline'}},
            # {'test_id': 10, 'configs': {'system': 'TMO'}},
            # {'test_id': 10, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 11, 'configs': {'system': 'baseline'}},
            # {'test_id': 11, 'configs': {'system': 'TMO'}},
            # {'test_id': 11, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 12, 'configs': {'system': 'baseline'}},
            # {'test_id': 12, 'configs': {'system': 'TMO'}},
            # {'test_id': 12, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 17, 'configs': {'system': 'baseline'}},
            # {'test_id': 17, 'configs': {'system': 'TMO'}},
            # {'test_id': 17, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 14, 'configs': {'system': 'baseline'}},
            # {'test_id': 14, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 15, 'configs': {'system': 'baseline'}},
            # {'test_id': 15, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 16, 'configs': {'system': 'baseline'}},
            # {'test_id': 16, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 25, 'configs': {'system': 'baseline'}},
            # {'test_id': 25, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '14-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '14-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '16-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '16-sp1', 'configs': {'system': 'FaaSMem'}},

            # {'test_id': '0-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp1', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp2', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp2', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '0-sp3', 'configs': {'system': 'baseline'}},
            # {'test_id': '0-sp3', 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': '3-sp1', 'configs': {'system': 'baseline'}},
            # {'test_id': '3-sp1', 'configs': {'system': 'FaaSMem'}},
        ]},

        'float_operation': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.3}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'matmul': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1.1}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'linpack': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.65}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'image_processing': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1.3}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'chameleon': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.5}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'pyaes': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.9}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'gzip_compression': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 0.4}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},
        'json_dumps_loads': {'configs': {'raw_memory': 177, 'cpu': 0.5, 'exec_duration': 1}, 'tests': [
            # {'test_id': 2, 'configs': {'system': 'baseline'}},
            # {'test_id': 2, 'configs': {'system': 'TMO'}},
            # {'test_id': 2, 'configs': {'system': 'FaaSMem'}},
            #
            # {'test_id': 60, 'configs': {'system': 'baseline'}},
            # {'test_id': 60, 'configs': {'system': 'TMO'}},
            # {'test_id': 60, 'configs': {'system': 'FaaSMem'}},

            # {'test_id': 86, 'configs': {'system': 'DAMON'}},
            # {'test_id': 86, 'configs': {'system': 'baseline'}},
        ]},

    }

    for function_name, entry in target_functions.items():
        common_configs = entry['configs']
        for test in entry['tests']:
            test_info = general_tests[test['test_id']]
            now_configs = {}
            now_configs.update(common_configs)
            now_configs.update(test['configs'])
            test_to_one(function_name,
                        test_info['trace_id'], test_info['start_idx'], test_info['exp_duration'],
                        now_configs)


test_to_all()
