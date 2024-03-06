import sys
sys.path.append('../../')
from common_lib.draw_base import *


# Ablation
function_name = 'bert'
# trace_id = 0
# start_idx = 8967
# duration = 28800
trace_id = 3
start_idx = 52391
duration = 28800

labels = ['Baseline', 'FaaSMem', 'FaaSMem w/o Packet', 'FaaSMem w/o Semi-warm']

fig, ax1 = plt.subplots()
fig.set_size_inches(18, 7*18/20)

systems_memory_list = {}
normalize_memory = 0

for i, system in enumerate(['baseline', 'FaaSMem', 'FaaSMem-no-MGLRU', 'FaaSMem-no-semiwarm']):
    latency_data, memory_data = load_form_azure_trace_test(
        function_names_mapping[function_name], trace_id, start_idx, duration, system, dir='ablation')
    systems_memory_list[system] = np.array(memory_data)
    print(system, np.average(systems_memory_list[system]) / (1024 ** 3))
    normalize_memory = max(normalize_memory, max(systems_memory_list[system]))

linestyles = ['solid', 'solid', 'dashdot', 'dotted']
tmp_system_colors = {
    'baseline': '#519872',
    'FaaSMem': '#472B62',
    'FaaSMem-no-MGLRU': '#1C82AD',
    'FaaSMem-no-semiwarm': '#8CABFF'
}
tmp_system_colors = {
    'baseline': '#AAAAAA',
    'FaaSMem': '#3892bc',
    'FaaSMem-no-MGLRU': '#073345',
    'FaaSMem-no-semiwarm': '#bc6238'
}
for i, system in enumerate(['baseline', 'FaaSMem', 'FaaSMem-no-MGLRU', 'FaaSMem-no-semiwarm']):
    zorder = 0
    if system == 'FaaSMem-no-MGLRU':
        zorder = 1
    ax1.plot(systems_memory_list[system][8100:-3600] / (1024 ** 3), color=tmp_system_colors[system], linestyle=linestyles[i], linewidth=3, label=labels[i], zorder=zorder)
# for i in np.arange(1, 4, 2):
#     ax1.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)

ax1.legend(ncol=2,loc='upper right',fontsize=28, handlelength=1,columnspacing=0.5,handletextpad=0.3,borderaxespad=0.2)

ax1.set_xlim(0 - 200, 3600 * 5 -700)
# ax1.set_ylim(-0.2, 8)
ax1.set_xticks(np.arange(0, 3600 * 5, 3600))

ax1.set_xticklabels([str(i) for i in range(5)])

ax1.set_xlabel('Timeline (h)')
ax1.set_ylabel('Local Memory (GB)')
plt.savefig(f'fig_a_top' + '.pdf', bbox_inches='tight')
