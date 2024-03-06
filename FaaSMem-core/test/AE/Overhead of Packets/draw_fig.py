import sys
sys.path.append('../../')
from common_lib.draw_base import *

# mglru_barrier_overhead

fig, ax1 = plt.subplots()
fig.set_size_inches(19*6/7, 5*6/7)

barriers_functions_durations = {'runtime': [], 'init': [], 'rollback': []}

for function_name in functions_all:
    mglru_durations = load_from_mglru_barrier_overhead(
        function_names_mapping[function_name])
    barriers_functions_durations['runtime'].append(
        np.average(
            np.array([x[0] for x in mglru_durations])) * 1000 - 3)
    barriers_functions_durations['init'].append(
        np.average(
            np.array([x[1] for x in mglru_durations])) * 1000 - 3)
    roll_back_times = []
    for entry in mglru_durations:
        roll_back_times.extend(entry[3:])
    barriers_functions_durations['rollback'].append(np.average(roll_back_times) * 1000 - 3)
print(barriers_functions_durations['runtime'])
print(barriers_functions_durations['init'])
print(barriers_functions_durations['rollback'])
x_cnt = len(functions_all)
x = np.arange(x_cnt)

bar_width = 0.27
offset = [bar_width * -1, 0, bar_width * 1]

tmp_period_colors = {
    'runtime': colors[0],
    'init': colors[1],
    'rollback': colors[2],
}
tmp_period_labels = {
    'runtime': 'Runtime-Init Barrier',
    'init': 'Init-Execution Barrier',
    'rollback': 'Periodic Rollback'
}

for i, period in enumerate(['runtime', 'init', 'rollback']):
    ax1.bar(
        x + offset[i],
        barriers_functions_durations[period],
        color=tmp_period_colors[period], width=bar_width, label=tmp_period_labels[period],
        edgecolor='white', hatch = "//")

for i in np.arange(2.5, 12.5, 2.5):
    ax1.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)

ax1.set_yticks(np.arange(0, 11, 2.5))
ax1.set_yticklabels(np.arange(0, 11, 2.5))

ax1.set_xticks(x)
tmp_functions = functions_all.copy()
tmp_functions[7] = 'chame.'
ax1.set_xticklabels(tmp_functions, rotation=20)
ax1.set_xlim(-0.5, x_cnt - 0.5)
ax1.set_ylabel('Overhead (ms)')
ax1.legend(ncol=1,loc='upper right',fontsize=28, handlelength=1,columnspacing=0.5,handletextpad=0.3,borderaxespad=0.2)

plt.savefig('fig' + '.pdf', bbox_inches='tight')
