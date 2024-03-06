#!/bin/bash

set -e

add-apt-repository -y ppa:deadsnakes/ppa
apt install -y python3.8 python3.8-distutils python3-virtualenv

virtualenv venv --python=python3.8
source venv/bin/activate
which python
pip install -r requirements.txt

unzip -d trace trace/trace_tidy.zip

apt install -y iptables arptables ebtables
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get -y install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

wget -P benchmark/translator/bert/model https://huggingface.co/google-bert/bert-base-uncased/resolve/main/pytorch_model.bin

cd scripts
bash image_setup.bash


