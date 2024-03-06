import sys
sys.path.append('../../')
from common_lib.draw_base import *

fig, (ax1, ax2) = plt.subplots(2, 1, gridspec_kw=dict(height_ratios=[5, 4]), constrained_layout=True)
fig.set_size_inches(36 * 6 / 7, 6)
benchmark_cnt = len(functions_all)

bar_width = 0.175
space = 0.015
trace_id = 2
start_idx = 502
duration = 3600

x = np.arange(benchmark_cnt)
x1 = np.array([i * (bar_width + space) for i in range(-1, 2)])
x2 = [x + i * (bar_width + space) for i in range(-1, 2)]
systems_values = {}

systems_draw_seq = ['baseline', 'TMO', 'FaaSMem']

for system in systems_draw_seq:
    systems_values[system] = {'latency_P95': [], 'memory_avg': []}
    for function_name in functions_all:
        tmp_debug = False
        if function_name == 'bert':
            tmp_debug = True
        latency_data, memory_data = load_form_azure_trace_test(
            function_names_mapping[function_name], trace_id, start_idx, duration, system, in_debug=tmp_debug)
        systems_values[system]['latency_P95'].append(np.percentile(latency_data, 95))
        systems_values[system]['memory_avg'].append(np.average(memory_data))
    systems_values[system]['latency_P95'] = np.array(
        systems_values[system]['latency_P95'])
    systems_values[system]['memory_avg'] = np.array(
        systems_values[system]['memory_avg'])

for i, function_name in enumerate(functions_all):
    memory_list = []
    for system in systems_draw_seq:
        memory_list.append(systems_values[system]['memory_avg'][i] / systems_values['baseline']['memory_avg'][i])
    ax1.plot(x1 + i, memory_list, color=colors[4], linewidth=2, zorder=1)
for i, system in enumerate(systems_draw_seq):
    marker_size = 300
    if system == 'FaaSMem':
        marker_size = 350
    ax1.scatter(x2[i],
                systems_values[system]['memory_avg'] / systems_values['baseline']['memory_avg'],
                color=system_color[system], marker=system_marker[system], s=marker_size,
                label=systems_label_mapping[system])
    if system == 'baseline':
        continue
    for k, now_y in enumerate(systems_values[system]['memory_avg'] / systems_values['baseline']['memory_avg']):
        now_x = x2[i][k] + 0.05
        annotate_value = now_y - 1
        prefix = '+' if annotate_value > 0 else ''
        if k == 1 and trace_id == 60:
            if system == 'TMO':
                now_y += 0.04
            elif system == 'FaaSMem':
                now_y -= 0.04
        ax1.annotate(f'{prefix}{annotate_value:.1%}', xy=(now_x, now_y),
                     ha='left', va='center_baseline', fontsize=24, rotation=-10)
    for k, now_y in enumerate(systems_values[system]['latency_P95'] / systems_values['baseline']['latency_P95']):
        now_x = x2[i][k]
        annotate_value = now_y - 1
        prefix = '+' if annotate_value > 0 else ''
        ha = 'left' if system == 'FaaSMem' else 'center'
        # ax2.annotate(f'{prefix}{annotate_value:.1%}', xy=(now_x, now_y - 0.03),
        #              ha=ha, va='bottom', fontsize=22, rotation=15)

for i, system in enumerate(systems_draw_seq):
    ax2.bar(x2[i],
            systems_values[system]['latency_P95'] / systems_values['baseline']['latency_P95'],
            bar_width,
            color=system_color[system], align="center", label=systems_label_mapping[system],
            edgecolor='white', hatch="//")

ax1.get_xaxis().set_visible(False)  # 隐藏 ax1 的 x 轴刻度和标签
ax1.set_xlim(-0.5, benchmark_cnt - 0.2)
ax2.set_xlim(-0.5, benchmark_cnt - 0.2)

ax1.set_ylim(0)
ax2.set_ylim(0, 1.5)

ax2.set_xticks(x)
ax2.set_xticklabels(functions_all)

ax1.set_ylabel('Norm. Avg.\nLocal Memory')
ax2.set_ylabel('Norm. P95\nLatency')

ax1.axhline(y=1, color='tab:grey', linestyle='--', alpha=0.5)
ax1.axhline(y=0.5, color='tab:grey', linestyle='--', alpha=0.5)

ax2.axhline(y=1, color='tab:grey', linestyle='--', alpha=0.5)
ax2.axhline(y=1.1, color='tab:red', linewidth=2, linestyle='--', alpha=0.8)

ax2.annotate(f'+10%', xy=(benchmark_cnt - 0.5, 1.1),
             ha='center', va='bottom', fontsize=26, rotation=0, color='red')

ax1.axvline(x=2.5, color='tab:blue', linestyle='--', alpha=0.8, linewidth=2)
ax2.axvline(x=2.5, color='tab:blue', linestyle='--', alpha=0.8, linewidth=2)
# ax3 = ax1.twiny()
# ax3.set_xlim(-0.5, benchmark_cnt - 0.2)
# ax3.set_xticks([1, 6.5])
# ax3.set_xticklabels(['Applications', 'Micro-benchmarks'])
# ax3.tick_params(top=False)
# ax2.axhline(y=0.5, color='tab:grey', linestyle='--', alpha=0.5)

ax1.legend(ncol=3, loc='lower left', fontsize=28, handlelength=1, columnspacing=0.5, handletextpad=0.3,
           borderaxespad=0.2)
ax2.legend(ncol=3, loc='lower left', fontsize=28, handlelength=1, columnspacing=0.5, handletextpad=0.3,
           borderaxespad=0.2)

plt.savefig('fig_a' + '.pdf', bbox_inches='tight')