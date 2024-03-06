#!/bin/bash

set -e

cd drivers
make BACKEND=RDMA
