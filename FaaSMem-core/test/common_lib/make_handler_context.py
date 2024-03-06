import random

with open('../../common_lib/input_en.txt') as f:
    novel_en = f.read()


def gen_input_en(length):
    random_st = random.randint(0, len(novel_en) - length)
    return novel_en[random_st: random_st + length - 1]


pareto_config = {'graph_bfs': {'shape': 0.1, 'size': 100000},
                 'html_server': {'shape': 0.9, 'size': 50}}

functions_context = {'recognizer_adult': {},
                     'bert': {'input_en': gen_input_en(10)},
                     'float_operation': {'n': 100000},
                     'matmul': {'n': 1000},
                     'linpack': {'n': 1000},
                     'image_processing': {},
                     'video_processing': {},
                     'chameleon': {'num_of_rows': 100, 'num_of_cols': 100},
                     'pyaes': {'length_of_message': 10000, 'num_of_iterations': 1},
                     'model_training': {},
                     'gzip_compression': {'file_size': 1},
                     'json_dumps_loads': {},
                     'helsinki_translator': {'input_en': gen_input_en(200)}}  # file_size=10M


def get_pareto_idx(function_name):
    shape = pareto_config[function_name]['shape']
    size = pareto_config[function_name]['size']
    while True:
        x = random.paretovariate(shape)
        if x < size + 1:
            return int(x - 1)


def make_context(function_name):
    handler_context = {}
    if function_name in pareto_config:
        handler_context['id'] = get_pareto_idx(function_name)
        # tmp_set = set()
        # for i in range(10):
        #     tmp_set.add(get_pareto_idx(function_name))
        # handler_context['ids'] = list(tmp_set)
    elif function_name == 'bert':
        handler_context['input_en'] = gen_input_en(20)
    else:
        assert function_name in functions_context
        handler_context.update(functions_context[function_name])
    return handler_context

