import os
import subprocess
import sys
import time
import yaml

sys.path.append('../../')
from flask import Flask, request

proxy = Flask(__name__)
processes = [None, None, None]


def update_functions_configs(upd_configs):
    file_path = '../../benchmark/functions_info.yaml'
    with open(file_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    for entry in data['functions']:
        function_name = entry['function_name']
        if function_name in upd_configs:
            entry['configs'].update(upd_configs[function_name])
    with open(file_path, 'w') as f:
        yaml.dump(data, f)


@proxy.route('/clear')
def start():
    global processes
    for p in processes:
        if p is not None:
            p.kill()

    inp = request.get_json(force=True, silent=True)
    if 'upd_configs' in inp:
        update_functions_configs(inp['upd_configs'])
    os.system('docker rm -f $(docker ps -aq --filter label=FaaSMem)')
    os.system('damo stop')
    time.sleep(5)
    processes[0] = subprocess.Popen(['python3', 'proxy.py', addr, '8000'])
    time.sleep(5)
    return 'OK', 200


if __name__ == '__main__':
    addr = sys.argv[1]
    proxy.run('127.0.0.1', 7999, threaded=True)
