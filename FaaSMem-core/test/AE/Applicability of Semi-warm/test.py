import pandas as pd
import numpy as np
from tqdm import tqdm
import json
from queue import PriorityQueue

import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as tk
import numpy as np
import seaborn as sns
import math
import json
from matplotlib import gridspec
import matplotlib as mpl
# col_num = 100000

class ContainerWrapper:
    def __init__(self, now_time):
        self.start_time = now_time
        self.last_time = now_time
        self.serve_request_cnt = 0

    def cal_lifetime(self, keep_alive):
        return self.last_time + keep_alive - self.start_time


def make_tidy_trace():
    trace = pd.read_csv('AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt')
    print(trace)
    col_num = trace.shape[0]
    functions_events = {}
    max_timestamp = 0
    for i in tqdm(range(col_num)):
        entry = trace.iloc[i]
        function_id = entry['app'] + '.' + entry['func']
        ed = entry['end_timestamp']
        max_timestamp = max(max_timestamp, ed)
        duration = entry['duration']
        st = ed - duration
        if function_id not in functions_events:
            functions_events[function_id] = []
        functions_events[function_id].extend([{'timestamp': st, 'type': 0, 'request_id': i},
                                              {'timestamp': ed, 'type': 1, 'request_id': i, 'duration': duration}])

    function_ids = list(functions_events.keys())
    function_ids.sort(key=lambda x: len(functions_events[x]))
    print(len(function_ids))
    for function_id in function_ids:
        functions_events[function_id].sort(key=lambda x: (x['timestamp'], x['type']))

    output = {'function_ids': function_ids, 'functions_events': functions_events, 'per_function_invocations': []}
    for function_id in reversed(function_ids):
        events = functions_events[function_id]
        incoming_timestamps = []
        for e in events:
            if e['type'] == 0:
                incoming_timestamps.append(e['timestamp'])
        output['per_function_invocations'].append({'function_name': function_id,
                                                   'incoming_timestamps': incoming_timestamps})

    with open('trace_tidy.json', 'w') as f:
        json.dump(output, f)


def cal_percentile(data):
    percents = [50, 90, 95, 99]
    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(data, percent), '.3f'))


def analysis_for_container_recall():
    with open('trace_tidy.json', 'r') as f:
        data = json.load(f)
    keep_alive = 600
    function_ids = data['function_ids']
    functions_events = data['functions_events']

    container_idle_times = []
    for function_id in function_ids[-1:]:
        events = functions_events[function_id]
        idle_containers = []
        for e in events:
            if e['type'] == 0:
                if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > e['timestamp']:
                    container_idle_times.append(e['timestamp'] - idle_containers[-1])
                    idle_containers.pop()
            elif e['type'] == 1:
                idle_containers.append(e['timestamp'])
        # print(f'function exec cnt: {len(events) / 2}')
        # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    print('---')
    print(len(container_idle_times))
    cal_percentile(container_idle_times)
    with open('../result/idle_offload_simulation/container_recall.json', 'w') as f:
        json.dump({'container_idle_times': container_idle_times}, f)


def get_trace_cnt(data, trace_id):
    function_ids = data['function_ids']
    function_id = function_ids[-1 - trace_id]
    functions_events = data['functions_events']
    events = functions_events[function_id]
    return len(events) / 2 / 14


def analysis_for_container_recall_for_one_function(data, trace_id):
    keep_alive = 600
    function_ids = data['function_ids']
    function_id = function_ids[-1 - trace_id]
    functions_events = data['functions_events']

    container_idle_times = []

    events = functions_events[function_id]
    idle_containers = []
    for e in events:
        if e['type'] == 0:
            if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > e['timestamp']:
                container_idle_times.append(e['timestamp'] - idle_containers[-1])
                idle_containers.pop()
            # else:
            #     container_idle_times.append(600)
        elif e['type'] == 1:
            idle_containers.append(e['timestamp'])
    # print(f'function exec cnt: {len(events) / 2}')
    # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    # print('---')
    # print(len(container_idle_times))
    # cal_percentile(container_idle_times)
    if len(container_idle_times) == 0:
        container_idle_times.append(0)
    return container_idle_times


def cal_norm_idle_time(real_idle_time, semi_warm_start, semi_warm_duration):
    if real_idle_time < semi_warm_start:
        return real_idle_time
    if real_idle_time > semi_warm_start + semi_warm_duration:
        return semi_warm_start + (semi_warm_duration / 2)
    return (semi_warm_start + ((semi_warm_duration - (real_idle_time - semi_warm_start)) / semi_warm_duration + 1)
            * (real_idle_time - semi_warm_start) / 2)

def analysis_for_keep_alive_timeout_for_one_trace_v2(data, trace_id, keep_alive, exec_time, cold_exec_time):
    function_ids = data['function_ids']
    function_id = function_ids[-1 - trace_id]
    functions_events = data['functions_events']
    container_recall_times = []
    container_idle_times = []
    container_exec_total_time = 0
    end_timestamps = PriorityQueue()
    events = functions_events[function_id]
    idle_containers = []
    for e in events:
        if e['type'] != 0:
            continue
        now_timestamp = e['timestamp']
        while not end_timestamps.empty() and end_timestamps.queue[0] < now_timestamp:
            idle_containers.append(end_timestamps.get())
        if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > now_timestamp:
            tmp_idle_period = now_timestamp - idle_containers.pop(-1)
            container_recall_times.append(tmp_idle_period)
            container_idle_times.append(tmp_idle_period)
            end_timestamps.put(now_timestamp + exec_time)
            container_exec_total_time += exec_time
        else:
            end_timestamps.put(now_timestamp + cold_exec_time)
            container_exec_total_time += cold_exec_time
    assert len(container_recall_times) > 0
    for lst_time in idle_containers:
        container_idle_times.append(keep_alive)

    p99_recall = np.percentile(container_recall_times, 99)
    print(f'now p99 recall: {p99_recall}')
    faasmem_idle_time = 0
    base_idle_time = sum(container_idle_times)
    for real_idle_time in container_idle_times:
        faasmem_idle_time += cal_norm_idle_time(real_idle_time, p99_recall, 100)
    return container_exec_total_time, base_idle_time, faasmem_idle_time




def simulate(data, keep_alive):
    function_ids = data['function_ids']
    functions_events = data['functions_events']
    max_timestamp = 0
    for events in functions_events.values():
        max_timestamp = max(max_timestamp, events[-1]['timestamp'])
    total_exec_time = 0
    total_idle_time = 0

    total_exec_cnt = 0
    total_cold_cnt = 0
    for function_id in function_ids:
        events = functions_events[function_id]
        idle_containers = []
        func_exec_time = 0
        func_idle_time = 0
        durations = []
        for e in events:
            if e['type'] == 0:
                total_exec_cnt += 1
                if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > e['timestamp']:
                    func_idle_time += e['timestamp'] - idle_containers[-1]
                    idle_containers.pop()
                else:
                    total_cold_cnt += 1
            elif e['type'] == 1:
                func_exec_time += e['duration']
                idle_containers.append(e['timestamp'])
                durations.append(e['duration'])
        for last_time in idle_containers:
            func_idle_time += min(keep_alive, max_timestamp - last_time)
        total_exec_time += func_exec_time
        total_idle_time += func_idle_time
        # print(f'function exec cnt: {len(events) / 2}')
        # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    print('---')
    print(f'keep_alive: {keep_alive}')
    print(total_exec_time, total_idle_time, total_exec_time / (total_exec_time + total_idle_time))
    print(total_cold_cnt, total_exec_cnt, total_cold_cnt / total_exec_cnt)
    return {'keep_alive': keep_alive,
            'utilization': total_exec_time / (total_exec_time + total_idle_time),
            'cold_start': total_cold_cnt / total_exec_cnt}
    # cal_percentile(durations)


def simulate_for_per_container_request_cnt_cdf(data, keep_alive):
    function_ids = data['function_ids']
    functions_events = data['functions_events']
    max_timestamp = 0
    for events in functions_events.values():
        max_timestamp = max(max_timestamp, events[-1]['timestamp'])
    # total_exec_time = 0
    # total_idle_time = 0

    # total_exec_cnt = 0
    # total_cold_cnt = 0

    per_container_request_cnt_list = []
    for function_id in function_ids:
        events = functions_events[function_id]
        request_ids_container = {}
        idle_containers: list[ContainerWrapper] = []
        # func_exec_time = 0
        # func_idle_time = 0
        # durations = []
        for e in events:
            request_id = e['request_id']
            if e['type'] == 0:
                # total_exec_cnt += 1
                if len(idle_containers) > 0 and idle_containers[-1].last_time + keep_alive > e['timestamp']:
                    # func_idle_time += e['timestamp'] - idle_containers[-1]
                    now_container = idle_containers.pop()
                    request_ids_container[request_id] = now_container
                else:
                    # total_cold_cnt += 1
                    request_ids_container[request_id] = ContainerWrapper(e['timestamp'])
            elif e['type'] == 1:
                # func_exec_time += e['duration']
                request_ids_container[request_id].last_time = e['timestamp']
                request_ids_container[request_id].serve_request_cnt += 1
                idle_containers.append(request_ids_container[request_id])
                # durations.append(e['duration'])
        for container in idle_containers:
            per_container_request_cnt_list.append(container.serve_request_cnt)
            # func_idle_time += min(keep_alive, max_timestamp - last_time)
        # total_exec_time += func_exec_time
        # total_idle_time += func_idle_time
        # print(f'function exec cnt: {len(events) / 2}')
        # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    print('---')
    # print(f'keep_alive: {keep_alive}')
    # print(total_exec_time, total_idle_time, total_exec_time / (total_exec_time + total_idle_time))
    # print(total_cold_cnt, total_exec_cnt, total_cold_cnt / total_exec_cnt)
    return {
        # 'keep_alive': keep_alive,
        # 'utilization': total_exec_time / (total_exec_time + total_idle_time),
        # 'cold_start': total_cold_cnt / total_exec_cnt,
        'per_container_request_cnt_list': per_container_request_cnt_list
    }


def simulate_for_container_lifetime_cdf(data, keep_alive):
    function_ids = data['function_ids']
    functions_events = data['functions_events']
    max_timestamp = 0
    for events in functions_events.values():
        max_timestamp = max(max_timestamp, events[-1]['timestamp'])
    # total_exec_time = 0
    # total_idle_time = 0

    # total_exec_cnt = 0
    # total_cold_cnt = 0

    container_lifetime_list = []
    res = {'all': [], 'high': [], 'middle': [], 'low': []}
    for function_id in function_ids:
        events = functions_events[function_id]
        avg_daily_cnt = len(events) / 2 / 14
        request_ids_container = {}
        idle_containers: list[ContainerWrapper] = []
        # func_exec_time = 0
        # func_idle_time = 0
        # durations = []
        for e in events:
            request_id = e['request_id']
            if e['type'] == 0:
                # total_exec_cnt += 1
                if len(idle_containers) > 0 and idle_containers[-1].last_time + keep_alive > e['timestamp']:
                    # func_idle_time += e['timestamp'] - idle_containers[-1]
                    now_container = idle_containers.pop()
                    request_ids_container[request_id] = now_container
                else:
                    # total_cold_cnt += 1
                    request_ids_container[request_id] = ContainerWrapper(e['timestamp'])
            elif e['type'] == 1:
                # func_exec_time += e['duration']
                request_ids_container[request_id].last_time = e['timestamp']
                request_ids_container[request_id].serve_request_cnt += 1
                idle_containers.append(request_ids_container[request_id])
                # durations.append(e['duration'])
        for container in idle_containers:
            tmp_lifetime = container.cal_lifetime(keep_alive)
            res['all'].append(tmp_lifetime)
            if avg_daily_cnt >= 512:
                res['high'].append(tmp_lifetime)
            elif avg_daily_cnt >= 64:
                res['middle'].append(tmp_lifetime)
            else:
                res['low'].append(tmp_lifetime)
            # func_idle_time += min(keep_alive, max_timestamp - last_time)
        # total_exec_time += func_exec_time
        # total_idle_time += func_idle_time
        # print(f'function exec cnt: {len(events) / 2}')
        # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    print('---')
    cal_percentile(res['all'])
    cal_percentile(res['high'])
    cal_percentile(res['middle'])
    cal_percentile(res['low'])
    # print(f'keep_alive: {keep_alive}')
    # print(total_exec_time, total_idle_time, total_exec_time / (total_exec_time + total_idle_time))
    # print(total_cold_cnt, total_exec_cnt, total_cold_cnt / total_exec_cnt)
    return res


def cal_idle_memory_time(idle_duration, keepalive, start_offload_time):
    if idle_duration <= start_offload_time:
        return idle_duration
    else:
        return start_offload_time


def simulate_for_idle_offloading(data, keep_alive, start_offload_time):
    function_ids = data['function_ids']
    functions_events = data['functions_events']
    max_timestamp = 0
    for events in functions_events.values():
        max_timestamp = max(max_timestamp, events[-1]['timestamp'])
    total_exec_time = 0
    total_idle_time = 0

    total_exec_cnt = 0
    total_cold_cnt = 0
    total_idle_memory_time = 0
    for function_id in function_ids:
        events = functions_events[function_id]
        idle_containers = []
        func_exec_time = 0
        func_idle_time = 0
        durations = []
        for e in events:
            if e['type'] == 0:
                total_exec_cnt += 1
                if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > e['timestamp']:
                    func_idle_time += e['timestamp'] - idle_containers[-1]
                    total_idle_memory_time += cal_idle_memory_time(e['timestamp'] - idle_containers[-1],
                                                                   keep_alive,
                                                                   start_offload_time)
                    idle_containers.pop()
                else:
                    total_cold_cnt += 1
            elif e['type'] == 1:
                func_exec_time += e['duration']
                idle_containers.append(e['timestamp'])
                durations.append(e['duration'])
        for last_time in idle_containers:
            total_idle_memory_time += cal_idle_memory_time(min(keep_alive, max_timestamp - last_time),
                                                           keep_alive,
                                                           start_offload_time)
            func_idle_time += min(keep_alive, max_timestamp - last_time)
        total_exec_time += func_exec_time
        total_idle_time += func_idle_time
        # print(f'function exec cnt: {len(events) / 2}')
        # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    print('---')
    print(f'keep_alive: {keep_alive}, start_offload_time:{start_offload_time}, '
          f'total_idle_memory_time:{total_idle_memory_time}, total_idle_time:{total_idle_time}')
    return (total_idle_time - total_idle_memory_time) / (total_idle_time + total_exec_time)


def simulate_for_idle_offloading_for_one_function(data, trace_id, keep_alive,
                                                  start_offload_time):
    function_id = data['function_ids'][-1 - trace_id]
    functions_events = data['functions_events']
    max_timestamp = 0
    for events in functions_events.values():
        max_timestamp = max(max_timestamp, events[-1]['timestamp'])
    total_exec_time = 0
    total_idle_time = 0

    total_exec_cnt = 0
    total_cold_cnt = 0
    total_idle_memory_time = 0

    events = functions_events[function_id]
    idle_containers = []
    func_exec_time = 0
    func_idle_time = 0
    durations = []
    for e in events:
        if e['type'] == 0:
            total_exec_cnt += 1
            if len(idle_containers) > 0 and idle_containers[-1] + keep_alive > e['timestamp']:
                func_idle_time += e['timestamp'] - idle_containers[-1]
                total_idle_memory_time += cal_idle_memory_time(e['timestamp'] - idle_containers[-1],
                                                               keep_alive,
                                                               start_offload_time)
                idle_containers.pop()
            else:
                total_cold_cnt += 1
        elif e['type'] == 1:
            func_exec_time += e['duration']
            idle_containers.append(e['timestamp'])
            durations.append(e['duration'])
    for last_time in idle_containers:
        total_idle_memory_time += cal_idle_memory_time(min(keep_alive, max_timestamp - last_time),
                                                       keep_alive,
                                                       start_offload_time)
        func_idle_time += min(keep_alive, max_timestamp - last_time)
    total_exec_time += func_exec_time
    total_idle_time += func_idle_time
    # print(f'function exec cnt: {len(events) / 2}')
    # print(func_exec_time, func_idle_time, func_exec_time / func_idle_time)
    # print('---')
    # print(f'keep_alive: {keep_alive}, start_offload_time:{start_offload_time}, '
    #       f'total_idle_memory_time:{total_idle_memory_time}, total_idle_time:{total_idle_time}')
    return (total_idle_time - total_idle_memory_time) / (total_idle_time + total_exec_time)


def analysis_for_keep_alive_simulation():
    with open('trace_tidy.json', 'r') as f:
        data = json.load(f)
    res = []
    for keep_alive in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
        res.append(simulate(data, keep_alive))
    with open('../result/simulate_result.json', 'w') as f:
        json.dump(res, f)


def analysis_for_semiwarm_offload_simulation():
    with open('../../../trace/trace_tidy.json', 'r') as f:
        data = json.load(f)
    res = {'all': [], 'high': [], 'middle': [], 'low': []}
    keep_alive = 600
    for trace_id in range(len(data['function_ids'])):
        container_recall_times = analysis_for_container_recall_for_one_function(data, trace_id)
        p99 = np.percentile(container_recall_times, 99)
        saving_percent = simulate_for_idle_offloading_for_one_function(data, trace_id, keep_alive, p99)
        res['all'].append(saving_percent)
        avg_daily_cnt = get_trace_cnt(data, trace_id)
        if avg_daily_cnt >= 512:
            res['high'].append(saving_percent)
        elif avg_daily_cnt >= 64:
            res['middle'].append(saving_percent)
        else:
            res['low'].append(saving_percent)
    for k, v in res.items():
        print(k, len(v))
    if not os.path.exists('result'):
        os.mkdir('result')
    with open('result/semiwarm_offload_simulation_result.json', 'w') as f:
        json.dump(res, f)


def analysis_for_timeout_impact():
    with open('trace_tidy.json', 'r') as f:
        data = json.load(f)
    trace_id = 0
    exec_time = 0.15
    cold_exec_time = 1
    x=[[],[],[]]
    for keep_alive in [10, 60, 60*2, 60*5, 60*10, 60*20, 60*30]:
        print(f'keep_alive {keep_alive}')
        container_exec_total_time, base_idle_time, faasmem_idle_time = (
            analysis_for_keep_alive_timeout_for_one_trace_v2(data, trace_id, keep_alive, exec_time, cold_exec_time))
        base_total = container_exec_total_time + base_idle_time
        faasmem_total = (container_exec_total_time + faasmem_idle_time) * 0.6
        remote_total = base_total - faasmem_total
        x[0].append(base_total)
        x[1].append(faasmem_total)
        x[2].append(remote_total)

        print(f'exec: {container_exec_total_time} base_idle: {base_idle_time} faasmem_idle: {faasmem_idle_time}')
        print(f'faasmem remote {remote_total}')
        print(base_total, faasmem_total, faasmem_total / base_total)

    fig, ax1 = plt.subplots()
    fig.set_size_inches(12, 6)
    ax1.plot([10, 60, 60*2, 60*5, 60*10, 60*20, 60*30], x[0])
    ax1.plot([10, 60, 60*2, 60*5, 60*10, 60*20, 60*30], x[1])
    ax1.plot([10, 60, 60*2, 60*5, 60*10, 60*20, 60*30], x[2])
    fig.show()


def analysis_for_offload_target():
    with open('trace_tidy.json', 'r') as f:
        data = json.load(f)
    res = []
    keep_alive = 600
    trace_list = [1, 2, 3, 12, 14, 15, 60, 70, 90]
    target_offload_proportion_list = [0, 0.1, 0.3, 0.5, 0.7, 0.9]
    for trace_id in trace_list:
        container_recall_times = analysis_for_container_recall_for_one_function(data, trace_id)
        P95 = np.percentile(container_recall_times, 95)
        entry = {'trace_id': trace_id, 'P95': P95, 'total_idle_memory_time': []}
        res.append(entry)
        for offload_target in target_offload_proportion_list:
            target_local_memory_proportion = 1 - offload_target
            entry['total_idle_memory_time'].append(
                simulate_for_idle_offloading_for_one_function(
                    data, trace_id, keep_alive, P95, target_local_memory_proportion))
    with open('../result/idle_offload_simulation/simulate_idle_offload_target.json', 'w') as f:
        json.dump(res, f)


def analysis_for_per_container_request_cnt_cdf():
    with open('trace_tidy.json', 'r') as f:
        data = json.load(f)
    res = simulate_for_per_container_request_cnt_cdf(data, 600)
    with open('../result/per_container_request_cnt_cdf/per_container_request_cnt_cdf.json', 'w') as f:
        json.dump(res, f)


def analysis_for_container_lifetime_cdf():
    with open('../../../trace/trace_tidy.json', 'r') as f:
        data = json.load(f)
    res = simulate_for_container_lifetime_cdf(data, 600)
    if not os.path.exists('result'):
        os.mkdir('result')
    with open('result/container_lifetime_cdf.json', 'w') as f:
        json.dump(res, f)


def analysis_for_memory():
    filepath = 'AzureMemory/app_memory_percentiles.anon.d01.csv'
    data = pd.read_csv(filepath)
    memory_list = data['AverageAllocatedMb']
    print(np.percentile(memory_list, 0.1))


# make_tidy_trace()
# analysis_for_idle_offload_simulation()
# analysis_for_container_recall()
# analysis_for_offload_target()
# analysis_for_per_container_request_cnt_cdf()
analysis_for_container_lifetime_cdf()
analysis_for_semiwarm_offload_simulation()
# analysis_for_memory()
# analysis_for_timeout_impact()
