import os
import math
import yaml
from copy import deepcopy
from random import randint
from config import config

class FunctionInfo:
    def __init__(self, function_name, image_name, configs):
        self.function_name = function_name
        self.image_name = image_name
        self.max_containers = 16
        self.configs = {'tuning_id': 0,
                        'AB_TEST_FACTOR': 0.9,
                        'swappniess': 60,
                        'exec_tuning': False,
                        'semiwarm_delay': 120,
                        'lru_gen_interval': 1,
                        'reclaim_time_interval': 10,
                        'semiwarm': True,
                        'MGLRU': True,
                        'init_offload': True,
                        'test_type': 'normal'}
        self.configs.update(configs)

    @classmethod
    def parse(cls, config_path):
        functions_info = {}
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            for func in data['functions']:
                function_name = func['function_name']
                print(function_name)
                functions_info[function_name] = cls(function_name, func['image_name'], func['configs'])
        return functions_info

    def upd_configs(self, upd_configs: dict):
        self.configs.update(upd_configs)

    def get_exec_config(self, container_exec_cnt, exec_type):
        exec_configs = deepcopy(self.configs)
        exec_configs.update({'container_exec_cnt': container_exec_cnt})
        if exec_type == 'normal':
            return exec_configs
        if exec_type != 'tuning':
            raise Exception
        # exec_memory = int(math.ceil(self.configs['exec_tuning_memory'] * self.configs['AB_TEST_FACTOR']))
        # exec_configs.update({'exec_memory': exec_memory})
        exec_configs.update({'exec_memory': self.configs['exec_tuning_memory']})
        return exec_configs

