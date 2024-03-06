from gevent import monkey
monkey.patch_all()
import time

import gevent
import gc
import os
from gevent.pywsgi import WSGIServer
from flask import Flask, request

os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

proxy = Flask(__name__)
app_filename = 'app.py'


class Runner:
    def __init__(self):
        with open(app_filename, 'r') as f:
            self.code = compile(f.read(), app_filename, mode='exec')
        self.ctx = {}
        exec(self.code, self.ctx)

    def run(self, handler_context):
        self.ctx['handler_context'] = handler_context
        eval('handler(handler_context)', self.ctx)
        self.ctx.pop('handler_context')


runner = None


@proxy.route('/status')
def status():
    return 'OK', 200


@proxy.route('/init')
def init():
    global runner
    runner = Runner()
    return 'OK', 200


@proxy.route('/run')
def run():
    data = request.get_json(force=True, silent=True)
    handler_context = data['handler_context']
    st = time.time()
    runner.run(handler_context)
    ed = time.time()
    # gevent.spawn(gc.collect)
    return {'handler_context': handler_context, 'duration': ed - st}


if __name__ == '__main__':
    server = WSGIServer(('0.0.0.0', 5000), proxy)
    server.serve_forever()
