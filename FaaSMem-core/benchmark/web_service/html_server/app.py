import hashlib

html_list = []

for i in range(50):
    with open(f'data/{i}.mhtml', 'r') as f:
        html_list.append(f.read())


def handler(handler_context):
    # if 'ids' in handler_context:
    #     for tmp_id in handler_context['ids']:
    #         for i in range(3):
    #             hashlib.sha3_512(html_list[tmp_id].encode())
    #     return
    hashlib.sha3_512(html_list[handler_context['id']].encode())
    # tmp = html_list[handler_context['id']].encode()
    # handler_context['tmp'] = len(tmp)
