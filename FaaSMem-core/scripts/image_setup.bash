#!/bin/bash

set -e

docker build --no-cache -t faasmem_base ../src/container
bash ../benchmark/translator/create_image.sh
bash ../benchmark/web_service/create_image.sh
bash ../benchmark/graph/create_image.sh
bash ../benchmark/float_operation/create_image.sh
bash ../benchmark/matmul/create_image.sh
bash ../benchmark/linpack/create_image.sh
bash ../benchmark/image_processing/create_image.sh
bash ../benchmark/chameleon/create_image.sh
bash ../benchmark/pyaes/create_image.sh
bash ../benchmark/gzip_compression/create_image.sh
bash ../benchmark/json_dumps_loads/create_image.sh

docker image prune -f
