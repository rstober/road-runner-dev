# Road Runner
Road Runner is a high-level, user-friendly application that allows Bright CaaS customers to create completely configured, fully-operational, Bright-managed Linux clusters as quickly as possible. It saves user the time that they would otherwise be required to spend configuring the cluster.

## Puprpose
Road Runner was created to automate the process of creating fully-functional Bright Cluster Manager demo clusters. This cluster is suitable to demonstrate all of Bright's most important features.

* Slurm with the partitions: defq, gpu, jup
* Kubernetes (in a default configuration)
* Jupyter (in a default configuration)
* Autoscaler with one resource provider with both slurm and k8s workload engines configured
* Bright for Data Science packages installed on the head node
* cuda-driver, cuda-dcgm and Gnome desktop are installed in the compute node software image (cloned-image)
* Four compute nodes nodes:
  * cnode001 - k8s worker node
  * cnode002 - compute server in the slurm "jup" partition
  * cnode003 - compute server in the slurm "gpu" partition, managed by autoscaler ("aws" resource provider)
  * cnode004 - compute server in the slurm "gpu" partition, managed by autoscaler ("aws" resource provider)
* Six demo users (alice, charlie, david, frank, edgar, robert)
* Example jobs installed in /cm/shared/jobs
  * /cm/shared/jobs/submit-load - a script that can be used to submit random workload by the six users 
  * Root cron job that automatically periodically calls the submit-load script
* And Bright's Ansible collection, which Road Runner uses to configure the cluster
  * Because the playbooks are written to the headnode, they can be used to re-create the initial cluster, which is useful for DR and parallel upgrades.

## Quickstart
Log into krusty2 using your standard user account.
Use the cm-cod-aws command to create a cluster as you normally would, but add this --postbs command:
```

--postbs 'python3 -c "$(curl -fsSL https://raw.githubusercontent.com/rstober/road-runner/main/install.py)"' 

```
* Note the IP address as you will need it to connect to Bright View and Jupyter
* It will take somewhat less than two hours from start to finish. But once the head node comes up you can log in an view the progress (tail -f /var/log/cloud-init-output.log)
* The users all have the same password, which is in /root/.userpassword. use it to log into Jupyter as any of the configured users.
* If you intend to demo Jupyter Notebboks via Slurm start cnode002, then select queue "jup" in the custom kernel creator. You can use the "gpu" queue too, but this configuration ensures that there's at least one GPU node available that can be used in Jupyter
* If you want the users to run slurm jobs uncomment the root cron job (crontab -e). 
* The root cron job will periodically call /cm/shared/jobs/submit-load, but will stop submitting jobs once 20 are queued. 
* Autoscaler will automatically power on cnode003,cnode004 to run the workload.
## Support
Road Runner is alpha software, suitable only to be used for its stated purpose. 
* It currently only works on Bright CaaS for AWS
* But in the near future it may support Bright CaaS for OpenStack (krusty), Bright CaaS for Azure, and Bright CaaS for VMWare

## How it works
Road Runner reads a single YAML configuration file (install_config.yaml), writes several Ansible playbooks and then runs them. 

For example, this snippet of the default install_config.yaml file lists the three node categories that need to be created. 
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
The install.py script reads the cluster configuration file (install_config.yaml) file and creates a series of playbooks under install_dir/roles. For example, because the cluster configuration file contains the above "categories" section, the script wrote a playbook (install_dir/roles/categories/tasks/main.yaml) that will create the categories. 

Here's the playbook.
```

- name: clone default category -> cloned category
      brightcomputing.bcm92.category:
        name: cloned
        cloneFrom: default

    - name: set cloned category software image -> cloned-image
      brightcomputing.bcm92.category:
        name: cloned
        softwareImageProxy:
          parentSoftwareImage: cloned-image

    - name: clone default category -> k8s category
      brightcomputing.bcm92.category:
        name: k8s
        cloneFrom: default

    - name: set k8s category software image -> cloned-image
      brightcomputing.bcm92.category:
        name: k8s
        softwareImageProxy:
          parentSoftwareImage: cloned-image

    - name: clone default category -> jup category
      brightcomputing.bcm92.category:
        name: jup
        cloneFrom: default

    - name: set jup category software image -> cloned-image
      brightcomputing.bcm92.category:
        name: jup
        softwareImageProxy:
          parentSoftwareImage: cloned-image

```
Continuing with our example, it also created an Ansible vars file install_dir/roles/categories/vars/main.yaml

```
---

ansible_python_interpreter: /cm/local/apps/python3/bin/python

```
Once all the required playbooks have been written, the site.yaml playbook is run. When Ansible runs site.yaml, it runs the playbooks for each of the listed roles from their standard role directories, for example, for the "wlms" role the playbook in install_dir/roles/wlms/tasks/main.yaml. 
```

---
- hosts: all
  roles:
    - software_images
    - categories
    - nodes
    - packages
    - kubernetes
    - wlms
    - autoscaler
    - csps
    - jupyter
    - users
    - apps
    
```
## The other way to use Road Runner
Create a cluster in AWS. Road Runner does not yet discover what resources are available, so care must be taken to ensure that the cloud cluster contains the same number of nodes as are listed in the install_config.yaml file. 

1. Login to the Bright Customer Portal
2. Create a cluster on Demand. I have been creating clusters using the settings shown below:
![image](https://user-images.githubusercontent.com/809959/139966944-410166c5-18fb-44f1-92b9-6ff3161b8459.png)
3. Log in as root, and run the following command:
```
python3 -c "$(curl -fsSL https://raw.githubusercontent.com/rstober/road-runner/main/install.py)"
```

## Todo List
1. **Set the root password that was auto-generated on kruty**
2. **Auto-discover the resources that are available**
3. **Create a front-end that writes (and validates) the install_config.yaml file**
4. **Add support for krusty clusters**
