import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as tk
import numpy as np
import seaborn as sns
import math
import json
from matplotlib import gridspec
from matplotlib.ticker import FormatStrFormatter
import matplotlib as mpl

mpl.rcParams.update(mpl.rcParamsDefault)
plt.rcParams.update({'font.size': 30})
special_colors = ['#8ECFC9', '#FFBE7A', '#FA7F6F', '#82B0D2', '#BEB8DC', '#E7DAD2']

colors = ['#FFB6B9', '#BBDED6', '#61C0BF', '#61C0BF', '#FB8F81']
# colors = ['#CCCCCC', '#6D719A', '#6A2C70', '#FAE3D9', '#FB8F81']
# colors = ['#1B4F72', '#2878B5', '#9AC9DB', '#FAE3D9', '#FB8F81']
system_color = {'FaaSMem': colors[2],
                'FaaSMem-no-semiwarm': colors[1],
                'TMO': colors[1],
                'baseline': colors[0],
                'DAMON': colors[1],
                'OpenWhisk': '#f5616f',
                'Azure': '#14517c'}

system_marker = {'baseline': 'p',
                 'TMO': 'X',
                 'FaaSMem': '*'}
functions_all = ['bert', 'graph', 'web', 'float', 'matmul', 'linpack', 'image', 'chameleon', 'pyaes', 'gzip', 'json']
applications = ['bert', 'graph', 'web']
micro_benchmarks = ['float', 'matmul', 'linpack', 'image', 'chameleon', 'pyaes', 'gzip', 'json']
function_names_mapping = {
    'bert': 'bert', 'graph': 'graph_bfs', 'web': 'html_server',
    'float': 'float_operation', 'matmul': 'matmul', 'linpack': 'linpack', 'image': 'image_processing',
    'chameleon': 'chameleon', 'pyaes': 'pyaes', 'gzip': 'gzip_compression', 'json': 'json_dumps_loads'}
systems_label_mapping = {
    'baseline': 'Baseline',
    'FaaSMem': 'FaaSMem',
    'FaaSMem-no-semiwarm': 'FaaSMem-no-semiwarm',
    'TMO': 'TMO'
}


# with open('../trace/trace_tidy.json') as f:
#     trace_tidy = json.load(f)

def get_log_pos(st, ed, pos):
    st = math.log10(st)
    ed = math.log10(ed)
    pos = math.log10(pos)
    return (pos - st) / (ed - st)


def make_cdf(data_list):
    return np.sort(data_list), (np.arange(len(data_list)) + 1) / len(data_list)


def analysis_firing_timestamps(fire_list):
    fire_list.sort()
    buckets = []
    for i in range(1, len(fire_list)):
        buckets.append(fire_list[i] - fire_list[i - 1])
    return buckets

    st_time = fire_list[0]
    buckets = [0]
    for fire_time in fire_list:
        min_idx = int((fire_time - st_time) / 60)
        while len(buckets) - 1 < min_idx:
            buckets.append(0)
        buckets[min_idx] += 1
    return buckets


def load_for_rdma_vs_hdd(function_name):
    files = os.listdir('RDMAvsHDD')
    latency_list = []
    memory_list = []
    system_list = []
    for filename in files:
        if 'RDMAvsHDD' not in filename or function_name not in filename:
            continue
        filepath = os.path.join('RDMAvsHDD', filename)
        with open(filepath, 'r') as f:
            data_json = json.load(f)
        if 'RDMA' in data_json['args'].upper():
            now_system = 'RDMA'
        elif 'HDD' in data_json['args'].upper():
            now_system = 'HDD'
        else:
            raise Exception
        now_memory = data_json['configs']['exec_memory']
        for latency in data_json['latencies']:
            latency_list.append(latency)
            memory_list.append(now_memory)
            system_list.append(now_system)
    return pd.DataFrame({'latency': latency_list, 'memory': memory_list, 'system': system_list})


def load_form_azure_trace_test(function_name, trace_id, start_idx, duration, system, dir='result', in_debug=False,
                               load_firing_timestamps=False, loading_container_nums=False,
                               loading_rdma_bandwidth=False):
    files = os.listdir(dir)
    files.sort()
    latency_data = None
    memory_data = None
    firing_timestamps = None
    container_nums = None
    has_rdma_data = False
    total_network = 0
    in_debug = False
    for filename in files:
        if f'({system})' not in filename or '.json' not in filename:
            continue
        if f'{function_name}_{trace_id}_{start_idx}_{duration}' in filename:
            filepath = os.path.join(dir, filename)
            if 'Latency' in filename:
                # if latency_data is not None:
                #     print(f'warning: multiple json found: {filename}')
                with open(filepath, 'r') as f:
                    tmp_data = json.load(f)
                    latency_data = tmp_data['latencies']
                    firing_timestamps = tmp_data['firing_timestamps']
                if in_debug:
                    print('request_cnt', len(latency_data))
                    print(function_name, system, format(np.percentile(latency_data, 95), '.4f'), 's', filename)
            elif 'Globalmonitor' in filename:
                # if memory_data is not None:
                #     print(f'warning: multiple json found: {filename}')
                with open(filepath, 'r') as f:
                    tmp_data = json.load(f)
                    memory_data = tmp_data['memory_logs']
                    if loading_container_nums:
                        if 'container_nums' in tmp_data:
                            container_nums = tmp_data['container_nums']
                    if system == 'FaaSMem' or system == 'TMO':
                        if 'rdma_rcv' in tmp_data:
                            total_container_num_in_seconds = sum(float(x) for x in tmp_data['container_nums'])
                            # total_network = sum(float(x) for x in tmp_data['rdma_rcv'])
                            # print(system, f'RDMA rcv bandwidth: {format(total_network / total_container_num_in_seconds, ".6f")} M/s', )
                            total_network = sum(float(x) for x in tmp_data['rdma_rcv']) + sum(
                                float(x) for x in tmp_data['rdma_xmit'])
                            # print(system, f'RDMA bandwidth: {format(total_network / total_container_num_in_seconds, ".6f")} M/s', )
                if in_debug:
                    print(function_name, system, format(np.average(memory_data) / 1024 / 1024, '.0f'), 'M', filename)
    # if system == 'FaaSMem':
    #     print(system, f'trace-{trace_id}', f'RDMA bandwidth: {format(total_network / 3600, ".8f")} M/s', )
    if latency_data is None:
        latency_data = [0]
    if memory_data is None:
        memory_data = [0]
    if container_nums is None:
        container_nums = [0]
    if loading_container_nums and load_firing_timestamps:
        return latency_data, memory_data, firing_timestamps, container_nums
    if load_firing_timestamps and loading_rdma_bandwidth:
        return latency_data, memory_data, firing_timestamps, total_network / 3600
    if load_firing_timestamps:
        return latency_data, memory_data, firing_timestamps
    else:
        return latency_data, memory_data


def load_from_mglru_barrier_overhead(function_name, dir='result'):
    files = os.listdir(dir)
    mglru_durations = []
    for filename in files:
        if function_name in filename:
            filepath = os.path.join(dir, filename)
            with open(filepath, 'r') as f:
                mglru_durations = json.load(f)['mglru_durations']
    return mglru_durations


def load_form_colocation():
    files = os.listdir('colocation')
    latency_data = {}
    memory_data = {}
    for filename in files:
        filepath = os.path.join('colocation', filename)
        if 'Latency' in filename:
            with open(filepath, 'r') as f:
                latency_data = json.load(f)
        elif 'Globalmonitor' in filename:
            with open(filepath, 'r') as f:
                memory_data = json.load(f)
    return latency_data, memory_data


def load_from_AB_test(function_name, loop_cnt, decision_threshold, key='memory'):
    files = os.listdir('ABtest')
    for filename in files:
        if f'_ABtest_{function_name}_{loop_cnt}_{decision_threshold}_' in filename:
            filepath = os.path.join('ABtest', filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
            if key == 'memory':
                return data['res']
            elif key == 'time':
                return data['elapsed_time']
    return None

