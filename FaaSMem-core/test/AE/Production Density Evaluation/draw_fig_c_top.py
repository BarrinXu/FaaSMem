import sys
sys.path.append('../../')
from common_lib.draw_base import *

from scipy.interpolate import UnivariateSpline

fig, ax1 = plt.subplots()
fig.set_size_inches(5, 4)
bar_width = 0.175
space = 0.015
traces_info = {
    0: {'trace_id': 0, 'start_idx': 25011, 'exp_duration': 3600},
    2: {'trace_id': 2, 'start_idx': 502, 'exp_duration': 3600},
    3: {'trace_id': 3, 'start_idx': 27267, 'exp_duration': 3600},
    4: {'trace_id': 4, 'start_idx': 0, 'exp_duration': 3600},
    5: {'trace_id': 5, 'start_idx': 6168, 'exp_duration': 3600},
    6: {'trace_id': 6, 'start_idx': 35316, 'exp_duration': 3600},
    7: {'trace_id': 7, 'start_idx': 42167, 'exp_duration': 3600},
    8: {'trace_id': 8, 'start_idx': 52, 'exp_duration': 3600},
    9: {'trace_id': 9, 'start_idx': 0, 'exp_duration': 3600},
    10: {'trace_id': 10, 'start_idx': 0, 'exp_duration': 3600},
    # 11: {'trace_id': 11, 'start_idx': 16, 'exp_duration': 3600},
    12: {'trace_id': 12, 'start_idx': 0, 'exp_duration': 3600},
    17: {'trace_id': 17, 'start_idx': 0, 'exp_duration': 3600},

    14: {'trace_id': 14, 'start_idx': 2009, 'exp_duration': 3600},
    15: {'trace_id': 15, 'start_idx': 4003, 'exp_duration': 3600},
    16: {'trace_id': 16, 'start_idx': 3000, 'exp_duration': 3600},
    25: {'trace_id': 25, 'start_idx': 5017, 'exp_duration': 3600},

    60: {'trace_id': 60, 'start_idx': 0, 'exp_duration': 3600},

    '14-sp1': {'trace_id': 14, 'start_idx': 2370, 'exp_duration': 3600},
    # '16-sp1': {'trace_id': 16, 'start_idx': 3100, 'exp_duration': 3600},

    '0-sp1': {'trace_id': 0, 'start_idx': 13958, 'exp_duration': 3600},
    '0-sp2': {'trace_id': 0, 'start_idx': 29277, 'exp_duration': 3600},
    # '0-sp3': {'trace_id': 0, 'start_idx': 39348, 'exp_duration': 3600},
    '3-sp1': {'trace_id': 3, 'start_idx': 0, 'exp_duration': 3600},
}
functions_memory_quota = {
    'bert': [1280, 611],
    'graph': [256, 186],
    'web': [384, 256],
}
trace_cnt = len(traces_info)
x = np.arange(trace_cnt)
x1 = np.array([i * (bar_width + space) for i in range(-1, 2)])
x2 = [x + i * (bar_width + space) for i in range(-1, 2)]
systems_values = {}

application_id = 2

function_name = applications[application_id]
systems_draw_seq = ['baseline', 'FaaSMem']
traces_fire_buckets = []
for system in systems_draw_seq:
    systems_values[system] = {'latency_P95': [], 'memory_avg': [], 'total_requests': []}
    for trace_name, trace_info in traces_info.items():
        tmp_debug = False
        latency_data, memory_data, firing_timestamps = load_form_azure_trace_test(
            function_names_mapping[function_name],
            trace_info['trace_id'],
            trace_info['start_idx'],
            trace_info['exp_duration'],
            system, in_debug=tmp_debug, load_firing_timestamps=True)
        if len(latency_data) == 1:
            continue
        if system == 'FaaSMem':
            systems_values[system]['total_requests'].append(len(firing_timestamps))
            tmp_buckets = analysis_firing_timestamps(firing_timestamps)
            # print(len(tmp_buckets))
            traces_fire_buckets.append(np.array(tmp_buckets))

        systems_values[system]['memory_avg'].append(np.average(memory_data))
        systems_values[system]['latency_P95'].append(np.percentile(latency_data, 95))

    systems_values[system]['latency_P95'] = np.array(
        systems_values[system]['latency_P95'])
    systems_values[system]['memory_avg'] = np.array(
        systems_values[system]['memory_avg']) / 1024 / 1024
print(systems_values['baseline']['memory_avg'])
print(systems_values['FaaSMem']['memory_avg'])
traces_memory_info = []
for i in range(len(systems_values['baseline']['memory_avg'])):
    traces_memory_info.append((systems_values['FaaSMem']['total_requests'][i],
                               systems_values['baseline']['memory_avg'][i], systems_values['FaaSMem']['memory_avg'][i],
                               list(traces_info.keys())[i], np.average(traces_fire_buckets[i])))
traces_memory_info.sort()
print(traces_memory_info)
for entry in traces_memory_info:
    print(entry[0], entry[2], entry[2] / entry[1])
x_memory = [entry[0] / 60 for entry in traces_memory_info]
y_density = [functions_memory_quota[function_name][0] / (
            functions_memory_quota[function_name][0] - functions_memory_quota[function_name][1] * (
                1 - entry[2] / entry[1])) for entry in traces_memory_info]
ax1.scatter(x_memory, y_density, marker='^', s=150)
print(max(y_density))
parameter = np.polyfit(np.log(x_memory), y_density, 3)
p = np.poly1d(parameter)
ax1.plot(x_memory, p(np.log(x_memory)), linewidth=3, ms=14, label='Trends', color=colors[2])
# ax1.set_ylabel('Production\nDensity')
ax1.set_xlabel('Req per Minute')
ax1.set_ylim(1)
plt.savefig('fig_c_top' + '.pdf', bbox_inches='tight')

