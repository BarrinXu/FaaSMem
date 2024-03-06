from gevent import event


class RequestInfo:
    def __init__(self, request_id, function_name, runtime_configs, handler_context):
        self.request_id = request_id
        self.function_name = function_name
        self.runtime_configs: dict = runtime_configs
        self.handler_context = handler_context
        self.result = event.AsyncResult()
        self.exec_type = 'normal'
        self.duration = 0
        self.pgmjfault = 0
        self.return_infos = {}

    def set_tuning(self):
        self.exec_type = 'tuning'

    def gen_analyzer_log(self):
        return {'function_name': self.function_name,
                'request_id': self.request_id,
                'exec_config': self.runtime_configs,
                'duration': self.duration}
