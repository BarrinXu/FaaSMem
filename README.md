
This repository contains the prototype implementation of FaaSMem, the Fastswap ported to Linux 6.1, the 11 benchmarks, and the experiment workflow to run these benchmarks on CloudLab c6220 instances.

# Hardware and software config
* FaaSMem requires two nodes, and we strongly recommend to use the CloudLab c6220 instances. The c6220 instances satisfy the following requirements: 
  * Each node should have at least 16 cores and 64 GB memory, with 80 GB free disk space. 
  * Nodes should be connected through a RDMA-compatible network (e.g., InfiniBand).
* Each node should run Ubuntu 22.04.

# Installation

## Create the two nodes on CloudLab

* Click ``Experiments - Start Experiment``
1. Select a Profile: Select the default profile ``small-lan``
2. Parameterize: Number of Nodes: 2, Select OS image: UBUNTU 22.04, Optional physical node type: c6220

From now on, you have two nodes, a compute node and a memory node. Both nodes are running Ubuntu 22.04. MAKE SURE you are operating under root at anytime.

## Install the modified Linux 6.1 kernel on the compute node.

**Attention:** This script uses a kernel config file that is compatible with CloudLab c6220 instances, and is likely incompatible with other hardware instances, which may have to reconfigure the config file and modify the script.

Enter `linux-6.1.55-fastswap` directory.
Execute `bash install_kernel.sh`.

This script first installs the dependent tools needed to compile the kernel, then compiles and installs the kernel, and finally REBOOTS the machine. 


**Check:** After rebooting, please check that the currently running kernel is `6.1.55-fastswap`, by executing `uname -r` in a terminal. If not, make sure the kernel is successfully installed and listed, and then specify this kernel version to boot the machine.


## Install the software dependencies on the compute node.
Enter `FaaSMem-core` directory.
Execute `bash install_software.sh`.

This script first installs Python 3.8 and creates a Python-3.8 virtual environment `venv` under `FaaSMem-core`. It then unzip the Azure invocation trace. Finally, it installs Docker, builds images for 11 benchmarks.

**Check:** After the script is complete, there should be a `venv` dir under `FaaSMem-core`. You can also find 12 new images by executing `docker images`.

## Create a swapfile on the compute node
Enter `Fastswap` directory.
Execute `bash create_swapfile.sh`.

This script will require an interactive input, which is the directory to create the swapfile.
The directory MUST be under an ext4 partition, and has at least 32 GB free space.

**Check:** After the script is complete, there should be a 32 GB swapfile under the directory you specified.

## Install the RDMA driver and compile Fastswap on the compute node and the memory node.
First, on both nodes, enter `Fastswap` directory and execute `bash install_rdma.sh`.

This script installs the RDMA driver, compiles Fastswap framework, and REBOOTS the machine.

Second, after rebooting, enter `Fastswap` directory. 
On the compute node, execute `bash build_fastswap_driver.sh`. On the memory node, execute `bash build_fastswap_server.sh`.

**Check:** Execute `ibstat` on each node. You should see from the output that the network adapter is up.

# Experiment workflow

 MAKE SURE you are operating under root at anytime.

## Pre-experiment operations

**Attention:** The operations in this subsection need to be executed only once. DO NOT execute it multiple times UNLESS you have rebooted both the compute node and the memory node. If any node suffers a reboot during the experiment, the remote connection is broken. You need to REBOOT all nodes and perform the operations listed in this subsection again.




1. On the compute node, enter `Fastswap` directory, and execute `bash pre_experiment.sh`. 
This script will require an interactive input for the swapfile directory. 
It first disables the transparent huge page and the numa balancing. It then enable the swapfile created early before.

**Check:** Execute `swapon -s`, you will see the only one swapfile around 32 GB, which is exactly the one created before.

2. Configure the IP address for the compute node and the memory node. 

First, you need to obtain the adapter interface name, by executing `ibstat` in the terminal. 
In CloudLab c6220 instance, the name should be `ibp130s0`. 

Second, check the interface name exists in the output by executing `ifconfig -a`.

Third, assign IP for the interface of each node. For instance, execute `ifconfig ibp130s0 192.168.125.x/24` for the compute node, execute `ifconfig ibp130s0 192.168.125.y/24` for the memory node. Here, x and y MUST be different, and are RECOMMENDED to follow the suffix of node id in the CloudLab to avoid duplication with other users.

**Check:** Execute `ifconfig ibp130s0` on each node to verify the IP address you configured. Execute `ping 192.168.125.y` on the compute node.

3. On the memory node, open a window using screen or tmux. 
Then enter `Fastswap` directory.
Execute `bash run_fastswap_server.sh` to start the server for memory offloading. You can detach the window, DO NOT terminate it.

**Check:** The output of the script contains `listening on port 50000`.

4. On the compute node, enter `Fastswap` directory. 
Then execute `bash run_fastswap_driver.sh` to connect the memory node. The script will require two interactive input, the first is the compute node IP, and the second is the memory node IP.

**Check:** On the compute node, execute `dmesg | grep ctrl`, you can see `ctrl is ready for reqs`.

5. On the compute node, open three windows (Window-1, Window-2, Window-3) using screen or tmux. All of them MUST source the virtual environment `venv` under `FaaSMem-core`. DO NOT terminate them.

6. In Window-1, enter `FaaSMem-core/src/workflow_manager`, execute `python gateway.py`, which starts the gateway of FaaSMem to receive requests. In Window-2, enter `FaaSMem-core/src/workflow_manager`, execute `python test_server.py 127.0.0.1`, which starts the server of FaaSMem to process requests. DO NOT terminate them.


## Conduct each experiment

Each directory within `FaaSMem-core/test/AE` corresponds to one experiment.
You should use Window-3, enter each directory, and execute `python test.py` to conduct the experiment. We also offer a lite version, named `test_lite.py`, this script will only generate part results.
Once the experiment ends, a series of JSON files will be saved to the `result` subdirectory. See the following [Evaluation and expected results](#visualize) section to visualize the JSON files.

### Performance of Diverse Benchmarks

Estimated duration: 68 hours (19 hours for the lite version, which only test for benchmark bert, graph, and web).

visualization output: PDF graph in the current directory.

### Performance of Diverse Workloads

Estimated duration: 56 hours (19 hours for the lite version, which only test for benchmark bert).

visualization output: One Table in the terminal.

### Ablation Experiments

Estimated duration: 65 hours (32 hours for the lite version, which only test for the common case).

visualization output: PDF graph in the current directory.

### Applicability of Semi-warm

Estimated duration: 1 minute.

visualization output: PDF graph in the current directory.

### Overhead of Packets

Estimated duration: 2.5 hours.

visualization output: PDF graph in the current directory.

### Production Density Evaluation

Estimated duration: 65 hours (22 hours for the lite version, which only test for benchmark bert).

visualization output: PDF graph in the current directory.

# <a id="visualize"></a> Evaluation and expected results

Within each experiment directory, we prepare some draw scripts `draw*.py`.
The scripts also require the virtual environment `venv` under `FaaSMem-core`.
You can enter each directory, and execute `python draw*.py` to visualize the results. 
Each script will save a PDF format graph in the current directory, except that one script will output a table in the terminal. The graphs and tables generated can be compared with those in the paper.

# Kernel maintenance 

We provide a kernel patch of the modified Linux kernel, which is placed at `linux-6.1.55-fastswap/kernel.patch`.

First, you need a copy of the source of Linux kernel 6.1.55. Then you can apply the patch on it.
We outline the high level steps here.

```
wget https://mirrors.edge.kernel.org/pub/linux/kernel/v6.x/linux-6.1.55.tar.gz
tar -zxvf linux-6.1.55.tar.gz
cd linux-6.1.55
git init .
git add .
git commit -m "first commit"
git apply the_path_to_kernel.patch
```

