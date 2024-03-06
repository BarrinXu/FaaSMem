import ops
import sys
sys.path.append('../../')
from config import config

functions_configs = {
    'float_operation':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'matmul':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'linpack':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'image_processing':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'chameleon':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'pyaes':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'gzip_compression':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'json_dumps_loads':
        {'raw_memory': 177, 'cpu': 0.1, 'system': 'FaaSMem'},
    'graph_bfs':
        {'raw_memory': 885, 'cpu': 0.5, 'system': 'FaaSMem'},
    'html_server':
        {'raw_memory': 354, 'cpu': 0.2, 'system': 'FaaSMem'},
    'bert':
        {'raw_memory': 1770, 'cpu': 1, 'system': 'FaaSMem'},
}


for worker_ip in config.WORKERS_IP:
    ops.clean_worker(worker_ip, {'upd_configs': functions_configs})
for worker_ip in config.WORKERS_IP:
    ops.start_monitor(worker_ip)
