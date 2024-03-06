#!/bin/bash

set -e

apt update
apt install -y screen infiniband-diags opensm libibverbs-dev librdmacm-dev perftest rdma-core ibutils ibverbs-utils rdmacm-utils

reboot
