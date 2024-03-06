import sys
sys.path.append('../../')
from common_lib.draw_base import *


# semiwarm offload simulation across different functions CDF
# all 424
# high 28
# middle 76
# low 320
fig, ax1 = plt.subplots()
fig.set_size_inches(9*6/7, 6*6/7)
with open('result/semiwarm_offload_simulation_result.json') as f:
    data = json.load(f)
cdf_colors = ['#F08A5D', '#222831', '#B83B5E', '#6A2C70']
linestyles = ['solid', 'dashed', 'dashdot', 'dotted']
labels = ['All', 'High load', 'Middle load', 'Low load']
for i, function_type in enumerate(['all', 'high', 'middle', 'low']):
    x_list, y_list = make_cdf(data[function_type])
    ax1.plot(x_list, y_list,
             linewidth=3, linestyle=linestyles[i],
             ms=14, label=labels[i], color=cdf_colors[i])
for i in np.arange(0, 1.1, 0.25):
    ax1.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)
ax1.get_xaxis().set_major_formatter(tk.PercentFormatter(xmax=1))
# ax1.set_xlabel("Proportion of a container's lifetime\nthat fall into the semi-warm")
ax1.set_xlabel('Semi-warm Time / Total Lifetime')
ax1.set_ylabel('CDF')
ax1.legend(ncol=1,loc='lower right',fontsize=28, handlelength=1,columnspacing=0.5,handletextpad=0.3,borderaxespad=0.2)
plt.savefig('fig_left' + '.pdf', bbox_inches='tight')
