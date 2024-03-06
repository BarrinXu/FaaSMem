from gevent import monkey

monkey.patch_all()
import gevent
import sys

sys.path.append('../../')
import time
import random
from config import config
from gevent.pywsgi import WSGIServer
from flask import Flask, request
import requests

worker_nums = len(config.WORKERS_IP)
app = Flask(__name__)


@app.route('/run')
def run():
    data = request.get_json(force=True, silent=True)
    request_id = data['request_id']
    function_name = data['function_name']
    runtime_configs = data['runtime_configs']
    handler_context = data['handler_context']
    worker_id = random.randrange(0, worker_nums)
    st = time.time()
    r = requests.get(f'http://{config.WORKERS_IP[worker_id]}:8000/run',
                     json={'request_id': request_id, 'function_name': function_name,
                           'runtime_configs': runtime_configs, 'handler_context': handler_context})
    ed = time.time()
    res = r.json()
    res['latency'] = ed - st
    return res


@app.route('/upd_configs')
def upd_configs():
    data = request.get_json(force=True, silent=True)
    e = []
    for worker_ip in config.WORKERS_IP:
        e.append(gevent.spawn(requests.get, f'http://{worker_ip}:8000/upd_configs',
                              json=data))
    gevent.joinall(e)
    return 'OK', 200


if __name__ == '__main__':
    server = WSGIServer(('127.0.0.1', 7000), app)
    server.serve_forever()
