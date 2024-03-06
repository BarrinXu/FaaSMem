import json
from urllib.request import urlopen
import time


def handler(handler_context):
    # Simulate download
    time.sleep(0)

    start = time.time()
    with open('search.json') as f:
        json_data = json.load(f)
    str_json = json.dumps(json_data, indent=4)
    latency = time.time() - start
