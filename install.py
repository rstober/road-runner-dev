#!/usr/bin/env python3

import yaml
import json
import os
import shutil
import glob
import stat
import pprint
import subprocess
import string
import secrets

install_dir = "/root/.road-runner"

# concatenate temporary files in dirName to fileName then return fileName
def concatenateFiles(dirName, createFile):
    
    with open(createFile, "w") as outfile:
        for filename in os.listdir(dirName):
            with open(dirName + '/' + filename) as infile:
                contents = infile.read()
                outfile.write(contents)
                
    return createFile
    
def cleanTmpDir(dirName):

    files = glob.glob(dirName + '/*.yaml')

    for f in files:
        try:
            os.remove(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))
            
def generatePassword(length):
 
    alphabet = string.ascii_letters + string.digits + '!@#$%^'
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    
    return password

if __name__ == '__main__':

    # delete the installation directory if it exists
    isExist = os.path.exists(install_dir)
    if isExist:
        shutil.rmtree(install_dir)
    
    # create the installation director
    os.mkdir(install_dir)
    
    # always cd into install_dir
    os.chdir(install_dir)
    
    # install git
    os.system("dnf install -y git")
    
    # install road-runner distribution
    os.system("git clone https://github.com/rstober/road-runner-dev.git %s" % install_dir)
    
    # load the python3 module
    exec(open('/cm/local/apps/environment-modules/4.5.3/Modules/default/init/python.py').read())
    module('load','python3')
    
    # read in client configuration
    stream = open('install_config.yaml', 'r')
    dictionary = yaml.safe_load(stream)
    
    with open('/etc/ansible/facts.d/custom.fact', 'w') as write_file:
        json.dump(dictionary, write_file, indent=2)
    
    # install ansible base
    os.system('pip install ansible==' + dictionary["ansible_version"])
    
    # install the brightcomputing.bcm Ansible collection
    os.system("ansible-galaxy collection install brightcomputing.bcm")
   
    # copy the CMSH aliases, bookmarks and scriptlets to their proper locations
    shutil.copyfile("cmshrc", "/root/.cmshrc")
    shutil.copyfile("bookmarks-cmsh", "/root/.bookmarks-cmsh")
    shutil.copyfile("du.cmsh", "/root/.cm/cmsh/du.cmsh")
    shutil.copyfile("cu.cmsh", "/root/.cm/cmsh/cu.cmsh")
    shutil.copyfile("si.cmsh", "/root/.cm/cmsh/si.cmsh")
    shutil.copyfile("dp.cmsh", "/root/.cm/cmsh/dp.cmsh")
    shutil.copyfile("ansible.cfg", "/root/.ansible.cfg")
    
    if "update_head_node" in dictionary: 
    
        index=0
        
        os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/usr/bin/python'
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" dnf-update-pb.yaml'.format(index=index))
        
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/dnf-update.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
        
    if "software_images" in dictionary:
    
        index=0
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" create-software-image-preamble-pb.yaml'.format(index=index))
    
        for image in dictionary["software_images"]:
        
            index+=1
        
            os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/cm/local/apps/python3/bin/python'
            
            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} image_name={image_name} clone_from={clone_from} image_path={image_path}" create-software-image-pb.yaml'.format(index=index, image_name=image["name"], clone_from=image["clone_from"], image_path=image["path"]))
            
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/software-images.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
        
    if "categories" in dictionary:
    
        index=0
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" create-category-preamble-pb.yaml'.format(index=index))
    
        for category in dictionary["categories"]:
        
            index+=1
        
            os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/cm/local/apps/python3/bin/python'
            
            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} category_name={name} clone_from={clone_from} software_image={software_image}" create-category-pb.yaml'.format(index=index, name=category["name"], clone_from=category["clone_from"], software_image=category["software_image"]))
            
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/categories.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
            
    if "nodes" in dictionary:
    
        index=0
    
        os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/cm/local/apps/python3/bin/python'
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" configure-nodes-preamble-pb.yaml'.format(index=index))
    
        for node in dictionary["nodes"]:
        
            index+=1
            
            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} category={category} hostname={hostname} power_control={power_control}" configure-nodes-pb.yaml'.format(index=index, category=node["category"], hostname=node["hostname"], power_control=node["power_control"]))
            
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/nodes.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
            
    if "packages" in dictionary:
    
        index=0
   
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" headnode-install-package-preamble-pb.yaml'.format(index=index))
    
        for package in dictionary["packages"]:
        
            os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/usr/bin/python'
            index +=1
            
            if package["target"] == "headnode":
            
                os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} package_name={package_name}" headnode-install-package-pb.yaml'.format(index=index, package_name=package["package_name"]))
                
            else:
                os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} package_name={package_name} target={target}" node-install-package-pb.yaml'.format(index=index, package_name=package["package_name"], target=package["target"]))
                
                if package["package_name"] == "cuda-driver":
                
                    index+=1
                    
                    os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} target={target}" patch-cuda-driver-service-file-pb.yaml'.format(index=index, target=package["target"]))
                    
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/packages.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
        
    if "kubernetes" in dictionary:
    
        index=0
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" install-k8s-preamble-pb.yaml'.format(index=index))
    
        for instance in dictionary["kubernetes"]:
        
            index+=1
        
            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} instance_name={instance_name} categories={categories}" install-k8s-pb.yaml'.format(index=index, instance_name=instance["name"], categories=instance["categories"]))
        
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/kubernetes.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
                    
    if "wlms" in dictionary:
    
        for wlm in dictionary["wlms"]:
        
            if wlm["name"] == "slurm":
            
                os.environ['ANSIBLE_PYTHON_INTERPRETER'] = '/cm/local/apps/python3/bin/python'
                index=0
            
                if wlm["constrain_devices"]:
                
                    os.system('ansible-playbook -ilocalhost, --extra-vars "wlm_name={wlm_name} index={index}" configure-wlm-pb.yaml'.format(wlm_name=wlm["name"], index=index))
            
                for queue in wlm["queues"]:
            
                    index+=1
                
                    os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} queue_name={queue_name} clone_from={clone_from} default_queue={default_queue} over_subscribe={over_subscribe} wlm_cluster={wlm_cluster}" clone-slurm-queue-pb.yaml'.format(index=index, queue_name=queue["queue_name"], clone_from=queue["clone_from"], default_queue=queue["default_queue"], over_subscribe=queue["over_subscribe"], wlm_cluster=queue["wlm_cluster"]))
            
                for overlay in wlm["configuration_overlays"]:
            
                    index+=1
                
                    os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} overlay_name={overlay_name} categories={categories} all_head_nodes={all_head_nodes}" create-configuration-overlay-pb.yaml'.format(index=index, overlay_name=overlay["name"], categories=overlay["categories"], all_head_nodes=overlay["allHeadNodes"]))
                
                    for role in overlay["roles"]:
                
                        index+=1
                    
                        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} overlay_name={overlay_name} role_name={role_name} wlm_cluster={wlm_cluster} queues={queues} sockets_per_board={sockets_per_board} cores_per_socket={cores_per_socket} threads_per_core={threads_per_core} slots={slots} real_memory={real_memory}" add-role-to-slurm-client-overlay-pb.yaml'.format(index=index, overlay_name=overlay["name"], role_name=role["name"], wlm_cluster=role["wlm_cluster"], queues=role["queues"], sockets_per_board=role["sockets_per_board"], cores_per_socket=role["cores_per_socket"], threads_per_core=role["threads_per_core"], slots=role["slots"], real_memory=role["real_memory"]))
                    
                        for resource in role["generic_resources"]:
                    
                            index+=1
                    
                            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} overlay_name={overlay_name} role_name={role_name} resource_name={resource_name} alias={alias} file={file} res_type={res_type} count={count} consumable={consumable} add_to_gres_config={add_to_gres_config}" add-resource-pb.yaml'.format(index=index, overlay_name=overlay["name"], role_name=role["name"], resource_name=resource["name"], alias=resource["alias"], file=resource["file"], res_type=resource["type"], count=resource["count"], consumable=resource["consumable"], add_to_gres_config=resource["add_to_gres_config"]))
            else:                
                print("Error: unsupported workload management system")
                exit()
                        
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/wlm.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
                        
    if "autoscaler" in dictionary:
    
        index=0
        
        os.system('ansible-playbook -ilocalhost, --extra-vars "index={index}" create-add-overlay-pb.yaml'.format(index=index))
        
        for role in dictionary["autoscaler"]["roles"]:
        
            index+=1
            
            os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} role_name={role_name} runInterval={runInterval} debug={debug}" create-add-role-to-auto-scaler-overlay-pb.yaml'.format(index=index, role_name=role["name"], runInterval=role["runInterval"], debug=role["debug"]))
            
            for provider in role["resource_providers"]:
            
                index+=1
            
                os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} provider_name={provider_name} templateNode={templateNode} startTemplateNode={startTemplateNode} stopTemplateNode={stopTemplateNode} nodeRange={nodeRange} networkInterface={networkInterface} defaultResources={defaultResources}" add-dynamic-resource-provider-pb.yaml'.format(install_dir=dictionary["install_dir"], index=index, provider_name=provider["provider_name"], templateNode=provider["templateNode"], startTemplateNode=provider["startTemplateNode"], stopTemplateNode=provider["stopTemplateNode"], nodeRange=provider["nodeRange"], networkInterface=provider["networkInterface"], defaultResources=provider["defaultResources"]))
                
            for engine in role["engines"]:
            
                index+=1
               
                if engine["type"] == "ScaleHpcEngine":
               
                    os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} engine_name={engine_name} workloads_per_node={workloads_per_node} priority={priority} wlm_cluster={wlm_cluster}" add-ScaleHpcEngine-pb.yaml'.format(install_dir=dictionary["install_dir"], index=index, engine_name=engine["name"], workloads_per_node=engine["workloadsPerNode"], priority=engine["priority"], wlm_cluster=engine["wlmCluster"]))
               
                elif engine["type"] == "ScaleKubeEngine":
               
                    os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} engine_name={engine_name} workloads_per_node={workloads_per_node} priority={priority} cluster={cluster}" add-ScaleKubeEngine-pb.yaml'.format(install_dir=dictionary["install_dir"], index=index, engine_name=engine["name"], workloads_per_node=engine["workloadsPerNode"], priority=engine["priority"], cluster=engine["cluster"]))
                   
                else:
                
                    print("Error: unsupported engine type")
                    exit()
               
                for tracker in engine["trackers"]:
               
                    index+=1
                    
                    if tracker["type"] == "ScaleHpcQueueTracker":
                   
                        os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} tracker_name={tracker_name} queue={queue} assign_category={assign_category} allowed_resource_providers={allowed_resource_providers} workloads_per_node={workloads_per_node}" add-ScaleHpcQueueTracker.yaml'.format(install_dir=dictionary["install_dir"], index=index, tracker_name=tracker["name"], queue=tracker["queue"], assign_category=tracker["assignCategory"], allowed_resource_providers=tracker["allowedResourceProviders"], workloads_per_node=tracker["workloadsPerNode"])) 
                    
                    elif tracker["type"] == "ScaleKubeNamespaceTracker":   

                        os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} tracker_name={tracker_name} controllerNamespace={controllerNamespace} assign_category={assign_category} allowed_resource_providers={allowed_resource_providers} workloads_per_node={workloads_per_node}" add-ScaleKubeNamespaceTracker.yaml'.format(install_dir=dictionary["install_dir"], index=index, tracker_name=tracker["name"], controllerNamespace=tracker["controllerNamespace"], assign_category=tracker["assignCategory"], allowed_resource_providers=tracker["allowedResourceProviders"], workloads_per_node=tracker["workloadsPerNode"]))

                    else:
                
                        print("Error: unsupported tracker type")
                        exit()                        
   
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/auto-scaler.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
        
    if "csps" in dictionary:
        
        index=0
    
        for csp in dictionary["csps"]:
            
            if csp["type"] == "aws":
            
                os.system('ansible-playbook -ilocalhost, --extra-vars "install_dir={install_dir} index={index} provider_name={provider_name} useMarketplaceAMIs={useMarketplaceAMIs}" config-ec2-csp.yaml'.format(install_dir=dictionary["install_dir"], index=index, provider_name=csp["name"], useMarketplaceAMIs=csp["useMarketplaceAMIs"]))
            
            else:
            
                print("Error: Unsupported cloud service provider type")
                exit()
                
            index+=1
                
        concatenateFiles(dictionary["tmp_dir"], dictionary["pb_dir"] + '/csps.yaml')
        cleanTmpDir(dictionary["tmp_dir"])
        
    if "jupyter" in dictionary:
    
        # download and install the AWS CLI
        os.system("curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\"")
        shutil.unpack_archive('awscliv2.zip', install_dir, 'zip')
        os.chmod("aws/install", stat.S_IEXEC)
        os.chmod("aws/dist/aws", stat.S_IEXEC)
        os.system("./aws/install")
        
        # write the playbook that installs Jupyter and opens port 8000 in the director security group
        os.system('ansible-playbook -ilocalhost, install-jupyter-pb.yaml')
        
    if "users" in dictionary:
        
        password=generatePassword(20)
        os.system('ansible-playbook -ilocalhost, --extra-vars "password={password}" add-users-pb.yaml'.format(password=password))
        
    if "apps" in dictionary:
    
        os.system('ansible-playbook -ilocalhost, install-apps-pb.yaml')
    
                
        