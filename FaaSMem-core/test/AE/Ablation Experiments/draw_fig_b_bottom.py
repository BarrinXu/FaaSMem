import sys
sys.path.append('../../')
from common_lib.draw_base import *



 # Ablation
function_name = 'bert'
trace_id = 0
start_idx = 8967
duration = 28800
# trace_id = 3
# start_idx = 52391
# duration = 28800





fig, (ax1, ax2) = plt.subplots(1, 2, gridspec_kw=dict(width_ratios=[7, 2]),constrained_layout = True)
fig.set_size_inches(15, 4)

systems_memory = {}
systems_latency_list = {}
normalize_memory = 0

for i, system in enumerate(['baseline', 'FaaSMem', 'FaaSMem-no-MGLRU', 'FaaSMem-no-semiwarm']):
    latency_data, memory_data = load_form_azure_trace_test(
        function_names_mapping[function_name], trace_id, start_idx, duration, system)
    systems_memory[system] = np.average(memory_data)
    systems_latency_list[system] = [
        np.average(latency_data),
        np.percentile(latency_data, 50),
        np.percentile(latency_data, 95),
        np.percentile(latency_data, 99)]
latency_sequence = ['AVG', 'P50', 'P95', 'P99']
# tmp_system_colors = {
#     'baseline': '#FFB6B9',
#     'FaaSMem': '#61C0BF',
#     'FaaSMem-no-MGLRU': '#6A2C70',
#     'FaaSMem-no-semiwarm': '#B83B5E'
# }
tmp_system_colors = {
    'baseline': '#CCCCCC',
    'FaaSMem': '#6A2C70',
    'FaaSMem-no-MGLRU': '#B83B5E',
    'FaaSMem-no-semiwarm': '#FFB6B9'
}
tmp_system_colors = {
    'baseline': '#AAAAAA',
    'FaaSMem': '#3892bc',
    'FaaSMem-no-MGLRU': '#073345',
    'FaaSMem-no-semiwarm': '#bc6238'
}
print(systems_memory)
print(systems_latency_list)

x = np.arange(len(latency_sequence))
bar_width = 0.18
bar_offset = np.array([-1.5, -0.5, 0.5, 1.5]) * bar_width

labels = ['Baseline', 'FaaSMem', 'FaaSMem w/o Packet', 'FaaSMem w/o Semi-warm']

tmp_idx = [0, 3, 2, 1]

for i, system in enumerate(['baseline', 'FaaSMem', 'FaaSMem-no-MGLRU', 'FaaSMem-no-semiwarm']):
    ax1.bar(x + bar_offset[tmp_idx[i]], systems_latency_list[system], bar_width, color=tmp_system_colors[system], align="center", label=labels[i], edgecolor='white',linewidth=2,hatch = "//")
ax1.legend(ncol=2,loc='lower left',fontsize=28, handlelength=1,columnspacing=0.5,handletextpad=0.3,borderaxespad=0.2)
ax1.set_ylabel('E2E Latency (s)')
ax1.set_xticks(x)
ax1.set_xticklabels(latency_sequence)
ax1.set_yticks([0, 0.05, 0.1, 0.15])
# ax1.set_yticklabels([0, 0.05, 0.10, 0.15, 0.20])

for i in np.arange(0.05, 0.19, 0.05):
    ax1.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)

x = np.arange(1)
for i, system in enumerate(['baseline', 'FaaSMem', 'FaaSMem-no-MGLRU', 'FaaSMem-no-semiwarm']):
    ax2.bar(x + bar_offset[tmp_idx[i]], np.array(systems_memory[system]) / (1024 ** 3), bar_width, color=tmp_system_colors[system], align="center", label=labels[i], edgecolor='white',linewidth=2,hatch = "//")
ax2.set_xticks([])
ax2.set_ylabel('Avg. Memory (GB) ')
ax2.set_xlim(-0.5, 0.5)
for i in np.arange(1, 3, 1):
    ax2.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)
plt.savefig(f'fig_b_bottom' + '.pdf', bbox_inches='tight')
