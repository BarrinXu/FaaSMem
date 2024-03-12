#!/bin/bash

apt update
apt install -y libssl-dev libelf-dev libncurses-dev screen flex bison zip
cp config-6.1.55-fastswapV7 .config
make -j$(nproc)
make modules -j$(nproc)
make headers -j$(nproc)
make headers_install
make modules_install -j$(nproc)
make install
reboot
