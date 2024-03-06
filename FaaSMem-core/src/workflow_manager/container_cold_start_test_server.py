import os
import subprocess
import sys
import time
import yaml
import docker
from docker import DockerClient
from docker.models.containers import Container
import requests

sys.path.append('../../')
from flask import Flask, request

proxy = Flask(__name__)
container_url = 'http://127.0.0.1:{}/{}'
docker_client = docker.from_env()


def test_cold_start(function_name, memory, test_):
    port = 19999
    durations = []
    for i in range(10):
        st = time.time()
        container: Container = docker_client.containers.run(function_name,
                                                            detach=True,
                                                            ports={'5000/tcp': str(port)},
                                                            labels=['FaaSMem'],
                                                            cpu_quota=int(100000 * 1),
                                                            mem_limit=f'{memory}M')
        while True:
            try:
                r = requests.get(container_url.format(port, 'status'))
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.001)
        ed = time.time()
        container.remove(force=True)
        if i >= 5:
            durations.append(ed - st)
        time.sleep(0.1)
    print(f'avg: {format(sum(durations) / len(durations), ".3f")}')
    return sum(durations) / len(durations)


@proxy.route('/test')
def start():
    data = request.get_json()
    duration = test_cold_start(data['function_name'], data['cold_start_memory'])
    return {'duration': duration}


if __name__ == '__main__':
    addr = sys.argv[1]
    proxy.run('0.0.0.0', 7998, threaded=True)
