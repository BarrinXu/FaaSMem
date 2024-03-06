#!/bin/bash

set -e

echo "Enter the IP of compute node"
read compute_ip

echo "Enter the IP of memory node"
read memory_ip


echo "sudo insmod drivers/fastswap_rdma.ko sport=50000 sip=\"$memory_ip\" cip=\"$compute_ip\" nq=8"
echo "wait a few seconds..."
sudo insmod drivers/fastswap_rdma.ko sport=50000 sip="$memory_ip" cip="$compute_ip" nq=8

echo "sudo insmod drivers/fastswap.ko"
sudo insmod drivers/fastswap.ko
