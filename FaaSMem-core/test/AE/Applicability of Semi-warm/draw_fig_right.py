import sys
sys.path.append('../../')
from common_lib.draw_base import *

# container lifetime CDF
fig, ax1 = plt.subplots()
fig.set_size_inches(8*6/7, 6*6/7)


with open('result/container_lifetime_cdf.json') as f:
    data = json.load(f)


x_ticks = [60 * 10, 60 * 20, 60 * 30, 60 * 40, 60 * 50, 60 * 60]  # 刻度值（秒为单位）
x_labels = ['10min', '20min', '', '40min', '','1h']  # 刻度标签
cdf_colors = ['#F08A5D', '#222831', '#B83B5E', '#6A2C70']
linestyles = ['solid', 'dashed', 'dashdot', 'dotted']
labels = ['All', 'High load', 'Middle load', 'Low load']

for i, now_label in enumerate(['all', 'high', 'middle', 'low']):
    if now_label == 'all':
        continue
    container_lifetime_cdf_list = data[now_label]
    list_sorted = np.sort(container_lifetime_cdf_list)
    cdf = np.arange(len(list_sorted)) / len(list_sorted)
    ax1.plot(list_sorted, cdf, linewidth=3, linestyle=linestyles[i],
             ms=14, label=labels[i], color=cdf_colors[i])
# ax1.set_xlim(0.8, 20000)
ax1.set_xscale('log')


# ax1.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1])
ax1.set_xlim(9 * 60, 65 * 60)
ax1.set_xticks(x_ticks)
ax1.set_xticklabels(x_labels)
ax1.set_xticks([], minor=True)
ax1.xaxis.set_tick_params(which='minor', bottom=False)


# ax1.axhline(y=0.95, color='tab:red', linestyle='--', alpha=0.7)

# x_p95 = recall_sorted[int(len(recall_sorted) * 0.95)]
# print(x_p95)
# ax1.axvline(x=x_p95, color='tab:red', linestyle='--', alpha=0.7)
# ax1.annotate('0.95', xy=(0.0007, 0.95), xytext=(0.00025, 0.87), color='red', fontsize=24, arrowprops=dict(arrowstyle='-', color='red'))
#
# ax1.scatter(x_p95, 0.95, s=100, color=colors[4])
# ax1.annotate("({:.0f}m, 0.95)".format(x_p95 / 60), xy=(x_p95, 0.95), xytext=(10, 0.81), arrowprops=dict(arrowstyle='-'), fontsize=24, color=colors[4])
#
# ax1.annotate("Offload start", xy=(120, 0.5), xytext=(4, 0.5), arrowprops=dict(arrowstyle='->'), fontsize=24, horizontalalignment='left', verticalalignment='center')

# bucket = [0 for i in range(10)]
# for t in recall_times:
#     bucket[int(t / 60)] += 1
# bars = ax2.bar(np.arange(0.5, 10.5, 1), [bucket[i]/len(recall_times) for i in range(10)], width=0.4, color=colors[4])
#
# for rect in bars:
#     height = rect.get_height()
#     ax2.annotate("{:.2%}".format(height), xy=(rect.get_x() + rect.get_width() / 2, height), xytext=(0, -3),
#                 textcoords="offset points", ha='center', va='bottom', rotation=15, fontsize=20)

# ax2.set_yticks([0, 0.333333, 0.666667, 1])
# ax2.set_ylim(-0.033333, 1.033333)
# ax1.set_xscale('log')
# ax1.set_xlim(0.01, 11)
ax1.set_ylabel('CDF')
ax1.set_xlabel('Container Lifetime')
for i in np.arange(0, 1.1, 0.25):
    ax1.axhline(y=i, color='tab:grey', linestyle='--', alpha=0.5)
# ax1.axvline(x=2, color='tab:grey', linestyle='--', alpha=0.5)
# ax1.yaxis.set_major_formatter(tk.PercentFormatter(xmax=1, decimals=0))

# ax1.set_zorder(ax2.get_zorder() + 1)
# ax1.patch.set_visible(False)


# fig, ax1 = plt.subplots()
# fig.set_size_inches(8, 4)
# ax1.plot(np.arange(len(rdma_throughput)), rdma_throughput / normalize_std, color="#7ccba2", linewidth=2, marker='$×$',
#          ms=14, label='RDMA')
# ax1.plot(np.arange(len(hdd_throughput)), hdd_throughput / normalize_std, color="#f7903d", linewidth=2, marker='$×$',
#          ms=14, label='HDD')

# ax1.set_xticklabels(memory)
# ax1.set_ylabel('Normalized\nThroughput')
# ax1.set_xlabel('Memory (MB)')
ax1.legend(ncol=1,loc='lower right',fontsize=28, handlelength=1,columnspacing=0.5,handletextpad=0.3,borderaxespad=0.2)
plt.savefig('fig_right' + '.pdf', bbox_inches='tight')
# plt.savefig('figures/' + 'container_lifetime_CDF' + '.svg', bbox_inches='tight')