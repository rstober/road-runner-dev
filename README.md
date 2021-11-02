# Road Runner
Road Runner is a high-level, user-friendly application that allows Bright CaaS customers to create a completely configured, fully-operational, Bright-managed Linux cluster in about one hour. 

## Support
Road Runner currently only works on Bright CaaS for AWS. But in the near future it is likely to support Bright CaaS for OpenStack (krusty), Bright CaaS for Azure, and Bright CaaS for VMWare as development progresses.

## How it works today
Road Runner reads a single YAML configuration file (install_config.yaml), and writes Ansible playbooks that can then be run to configure the cluster. 

For example, this snippet of the default install_config.yaml file list the three node categories that need to be created. 
```
categories:
  - name: cloned
    clone_from: default
    software_image: cloned-image
  - name: k8s
    clone_from: default
    software_image: cloned-image
  - name: jup
    clone_from: default
    software_image: cloned-image
```
The install.py script reads the install_config.yaml file and creates a playbook that will create the categories by cloning an existing category, in this case, the default category. Here's the Ansible playbook that results.
```
---
- hosts: all
  gather_facts: false

  tasks:

    - name: clone default category -> cloned category
      brightcomputing.bcm.category:
        name: cloned
        cloneFrom: default

    - name: set cloned category software image -> cloned-image
      brightcomputing.bcm.category:
        name: cloned
        softwareImageProxy:
          parentSoftwareImage: cloned-image

    - name: clone default category -> k8s category
      brightcomputing.bcm.category:
        name: k8s
        cloneFrom: default

    - name: set k8s category software image -> cloned-image
      brightcomputing.bcm.category:
        name: k8s
        softwareImageProxy:
          parentSoftwareImage: cloned-image

    - name: clone default category -> jup category
      brightcomputing.bcm.category:
        name: jup
        cloneFrom: default

    - name: set jup category software image -> cloned-image
      brightcomputing.bcm.category:
        name: jup
        softwareImageProxy:
          parentSoftwareImage: cloned-image
```

## How to use Road Runner today
Create a cluster in AWS. Road Runner does not yet discover what resources are available, so care must be taken to ensure that the cloud cluster contains the same number of nodes as are listed in the install_config.yaml file. 

1. Login to the Bright Customer Portal
2. Create a cluster on Demand. I have been creating clusters using the settings shown below:
![image](https://user-images.githubusercontent.com/809959/139966944-410166c5-18fb-44f1-92b9-6ff3161b8459.png)
3. Log in as root, and run the following command:
```
python3 -c "$(curl -fsSL https://raw.githubusercontent.com/rstober/road-runner-dev/main/install.py)"
```
Road Runner will write the playbooks to /root/.road-runner/pb
4. Run the playbooks as the user root
```
module load python3
cd /root/.road-runner
ansible-playbook -ilocalhost, --flush-cache configure-auto-scaler.yaml
```
