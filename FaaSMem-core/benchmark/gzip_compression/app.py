import time
import gzip
import os
import string
import random


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def handler(handler_context):
    file_size = int(handler_context['file_size'])
    file_write_path = '/proxy/file'

    start = time.time()
    with open(file_write_path, 'wb') as f:
        f.write(os.urandom(file_size * 1024 * 1024))
    disk_latency = time.time() - start

    with open(file_write_path, 'rb') as f:
        start = time.time()
        with gzip.open('/proxy/result.gz', 'wb') as gz:
            gz.writelines(f)
        compress_latency = time.time() - start
