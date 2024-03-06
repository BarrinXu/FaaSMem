from gevent import monkey

monkey.patch_all()
import sys

sys.path.append('../../')
from config import config
from gevent.pywsgi import WSGIServer
from flask import Flask, request
from workersp import WorkerSP
import logging

app = Flask(__name__)


class Dispatcher:
    def __init__(self):
        self.manager = WorkerSP(sys.argv[1], config.GATEWAY_IP,
                                min_port=20000, max_port=30000,
                                functions_info_path=config.FUNCTIONS_INFO_PATH)

    def run(self, request_id, function_name, runtime_configs, handler_context):
        res = self.manager.run(request_id, function_name, runtime_configs, handler_context)
        return res

    def upd_configs(self, function_name, upd_configs):
        self.manager.upd_configs(function_name, upd_configs)


dispatcher = Dispatcher()


@app.route('/upd_configs')
def config():
    data = request.get_json(force=True, silent=True)
    logging.info(f'upd_configs: {data}')
    for function_name, upd_configs in data.items():
        dispatcher.upd_configs(function_name, upd_configs)
    return 'OK', 200


@app.route('/start_monitor')
def start_monitor():
    dispatcher.manager.function_manager.global_monitor.start_collect()
    return 'OK', 200


@app.route('/end_monitor')
def end_monitor():
    monitor_logs = dispatcher.manager.function_manager.global_monitor.end_collect()
    return monitor_logs

@app.route('/run')
def run():
    data = request.get_json(force=True, silent=True)
    # logging.info('proxy receive incoming request %s', data)
    # print('proxy receive incoming request', data)
    request_id = data['request_id']
    function_name = data['function_name']
    runtime_configs = data['runtime_configs']
    handler_context = data['handler_context']
    res = dispatcher.run(request_id, function_name, runtime_configs, handler_context)
    return res


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%H:%M:%S', level='INFO')
    server = WSGIServer(('127.0.0.1', int(sys.argv[2])), app, log=None)
    server.serve_forever()
