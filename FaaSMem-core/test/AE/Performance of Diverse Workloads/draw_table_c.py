import sys
sys.path.append('../../')
from common_lib.draw_base import *

fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw=dict(height_ratios=[1, 1]),constrained_layout = True)
fig.set_size_inches(28, 7)
bar_width = 0.175
space = 0.015
traces_info = {
        0: {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 3600},
        # 2: {'trace_id': 2, 'start_idx': 502, 'exp_duration': 3600},
        3: {'trace_id': 3, 'start_idx': 27267, 'exp_duration': 3600},
        4: {'trace_id': 4, 'start_idx': 0, 'exp_duration': 3600},
        5: {'trace_id': 5, 'start_idx': 6168, 'exp_duration': 3600},
        6: {'trace_id': 6, 'start_idx': 35316, 'exp_duration': 3600},
        7: {'trace_id': 7, 'start_idx': 42167, 'exp_duration': 3600},
        # 60: {'trace_id': 60, 'start_idx': 0, 'exp_duration': 3600},
    }
trace_cnt = len(traces_info)
x = np.arange(trace_cnt)
x1 = np.array([i * (bar_width + space) for i in range(-1, 2)])
x2 = [x + i * (bar_width + space) for i in range(-1, 2)]
systems_values = {}

application_id = 2

function_name = applications[application_id]
systems_draw_seq = ['baseline', 'TMO', 'FaaSMem']

for system in systems_draw_seq:
    systems_values[system] = {'latency_P95': [], 'memory_avg': []}
    for i, trace_info in enumerate(traces_info.values()):
        tmp_debug = False
        latency_data, memory_data = load_form_azure_trace_test(
            function_names_mapping[function_name],
            trace_info['trace_id'],
            trace_info['start_idx'],
            trace_info['exp_duration'],
            system, in_debug=tmp_debug)
        systems_values[system]['latency_P95'].append(np.percentile(latency_data, 95))
        systems_values[system]['memory_avg'].append(np.average(memory_data))
    systems_values[system]['latency_P95'] = np.array(
        systems_values[system]['latency_P95'])
    systems_values[system]['memory_avg'] = np.array(
        systems_values[system]['memory_avg']) / 1024 / 1024

# print(systems_values)

for i in range(trace_cnt):
    print(f'{i + 1} ', end='')
    for system in ['baseline', 'TMO', 'FaaSMem']:
        # if system != 'baseline':
            # idx = round((1 - systems_values[system]["memory_avg"][i] / systems_values['baseline']["memory_avg"][i]) / 0.1)
            # idx = min(5, idx)
        print(f'& {format(systems_values[system]["latency_P95"][i], ".2f")} s & '
              f'{format(systems_values[system]["memory_avg"][i] / 1024, ".2f")} G ', end='')
    print('\\\\')

