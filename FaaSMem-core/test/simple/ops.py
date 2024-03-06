import requests
import numpy as np


def clean_worker(addr, data):
    r = requests.get(f'http://{addr}:7999/clear', json={})
    assert r.status_code == 200
    r = requests.get(f'http://{addr}:8000/upd_configs', json=data['upd_configs'])
    assert r.status_code == 200


def start_monitor(addr):
    r = requests.get(f'http://{addr}:8000/start_monitor')
    assert r.status_code == 200


def end_monitor(addr):
    r = requests.get(f'http://{addr}:8000/end_monitor')
    assert r.status_code == 200
    return r.json()


def cal_percentile(data_list, percentile_number=None):
    if percentile_number is not None:
        return np.percentile(data_list, percentile_number)
    percents = [50, 90, 95, 99]

    for percent in percents:
        print(f'P{percent}: ', format(np.percentile(data_list, percent), '.3f'))



