#!/bin/bash

set -e

echo "Enter a directory to create swapfile?"
read swapfile_dir

fallocate -l 32G $swapfile_dir/swapfile
chmod 600 $swapfile_dir/swapfile
mkswap $swapfile_dir/swapfile






