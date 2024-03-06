#!/bin/bash

set -e

echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
echo 0 > /proc/sys/kernel/numa_balancing

echo "Enter the directory which contains the swapfile."
read swapfile_dir

swapoff -a
swapon $swapfile_dir/swapfile

