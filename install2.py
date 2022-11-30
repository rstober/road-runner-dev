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
import datetime
import logging
import sys

install_dir = "/root/.road-runner"
begin_time = datetime.datetime.now()

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

file_handler = logging.FileHandler('/var/log/road-runner.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# concatenate temporary files in dirName to fileName then return fileName
def concatenateFiles(dirName, createFile):
    
    with open(createFile, "w") as outfile:
        for filename in os.listdir(dirName):
            with open(dirName + '/' + filename) as infile:
                contents = infile.read()
                outfile.write(contents)
                
    return createFile
    
def createDirectoryPath(dir):
    
    if not os.path.exists(dir):
        try:
            os.makedirs(dir)
        except OSError as error:
            print("Error: %s : %s" % (dir, error.strerror))
            return False
            
    return True
            
def cleanTmpDir(dirName):

    files = glob.glob(dirName + '/*.yaml')

    for file in files:
        try:
            os.remove(file)
        except OSError as error:
            print("Error: %s : %s" % (file, error.strerror))
            return False
            
    return True
            
def generatePassword(length):
 
    alphabet = string.ascii_letters + string.digits + '!@#$%^'
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    
    return password
    
def printBanner(text):
    
    str_length = len(text)
    dashes = int((80 - (str_length + 2)) / 2)
    
    print('=' * 80)
    print ("%s %s %s" % (('=' * (dashes - 2)), text, ('=' * (80 - dashes - str_length))))
    print('=' * 80)
   
    return True

if __name__ == '__main__':

    # # delete the installation directory if it exists
    # isExist = os.path.exists(install_dir)
    # if isExist:
        # shutil.rmtree(install_dir)
    
    # create the installation directory
    createDirectoryPath(install_dir)
    
    # always cd into install_dir
    os.chdir(install_dir)
    
    # install git
    #os.system("dnf install -y git")
    os.system("apt update")
    os.system("apt install -y git")
    
    # install road-runner distribution
    os.system("git clone https://github.com/rstober/road-runner-dev.git %s" % install_dir)
    
    # download the AWS CLI
    # os.system("curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\"")
    # shutil.unpack_archive('awscliv2.zip', install_dir, 'zip')
    # os.chmod("aws/install", stat.S_IEXEC)
    # os.chmod("aws/dist/aws", stat.S_IEXEC)
    
    # load the python3 module
    exec(open('/cm/local/apps/environment-modules/4.5.3/Modules/default/init/python.py').read())
    os.environ['MODULEPATH'] = '/cm/local/modulefiles:/cm/shared/modulefiles'
    module('load','python3')
    module('load','cmsh')
    
    # read the install_config.yaml file into a dictionary
    stream = open('install_config.yaml', 'r')
    config = yaml.safe_load(stream)
    
    # create the ansible facts.d directory
    createDirectoryPath('/etc/ansible/facts.d')
    
    # write the ansible custom.fact file
    with open('/etc/ansible/facts.d/custom.fact', 'w') as write_file:
       json.dump(config, write_file, indent=2)
    
    # install ansible base
    os.system('pip install ansible==' + config["ansible_version"])
    
    # install the brightcomputing.bcm92 Ansible collection
    os.system("ansible-galaxy collection install brightcomputing.bcm92")
    
    # create an ansible roles directory for each role
    roles = list(("power", "license", "networks", "software_images", "categories", "nodes", "users"))
    for role in roles:
        os.system("ansible-galaxy init --init-path roles/ %s" % role)
   
    # copy the CMSH aliases, bookmarks and scriptlets to their proper locations
    createDirectoryPath('/root/.cm/cmsh')
    shutil.copyfile('cmshrc', '/root/.cmshrc')
    shutil.copyfile('bookmarks-cmsh', '/root/.bookmarks-cmsh')
    shutil.copyfile('du.cmsh', '/root/.cm/cmsh/du.cmsh')
    shutil.copyfile('cu.cmsh', '/root/.cm/cmsh/cu.cmsh')
    shutil.copyfile('si.cmsh', '/root/.cm/cmsh/si.cmsh')
    shutil.copyfile('dp.cmsh', '/root/.cm/cmsh/dp.cmsh')
    shutil.copyfile('hosts', '/etc/ansible/hosts')
    shutil.copyfile('ansible.cfg', '/root/.ansible.cfg')
    
    printBanner('Preparing playbooks')
    
    if "license" in config:
    
        shutil.copyfile("default-ansible-vars", install_dir + "/roles/license/vars/main.yml")
        
        os.system('ansible-playbook -ilocalhost, install-license.yml')
        
    if "software_images" in config:
        
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/software_images/vars/main.yml")
        shutil.copyfile("default-ansible-vars", install_dir + "/roles/updates/vars/main.yml")
        
        os.system('ansible-playbook -ilocalhost, clone-software-images.yml')
        
        os.system('ansible-playbook -ilocalhost, append-kernel-modules.yml')
        
    if "categories" in config:
        
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/categories/vars/main.yml")
            
        os.system('ansible-playbook -ilocalhost, clone-categories.yml')
            
    if "nodes" in config:
    
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/nodes/vars/main.yml")
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/power/vars/main.yml")
        
        os.system('ansible-playbook -ilocalhost, clone-nodes.yml')
        
        os.system('ansible-playbook -ilocalhost, power-on-nodes.yml')
        
        #os.system('ansible-playbook -ilocalhost, wait-for-up.yml')
        
        os.system('ansible-playbook -ilocalhost, grab-image.yml')
        
    if "networks" in config:
        
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/networks/vars/main.yml")
        
        os.system('ansible-playbook -ilocalhost, clone-networks.yml')
            
    if "users" in config:
    
        shutil.copyfile("bright-ansible-vars", install_dir + "/roles/users/vars/main.yaml")
        
        for user in config["users"]:
            
            password=generatePassword(8)
            
            os.system('ansible-playbook -ilocalhost, -e "username={username} password={password}" add-user.yml'.format(username=user, password=password))
        
    # if "kubernetes" in config:
    
        # index=0
        
        # shutil.copyfile("bright-ansible-vars", install_dir + "/roles/kubernetes/vars/main.yaml")
    
        # for instance in config["kubernetes"]:
        
            # index+=1
        
            # os.system('ansible-playbook -ilocalhost, --extra-vars "index={index} instance_name={instance_name} categories={categories}" install-k8s-pb.yaml'.format(index=index, instance_name=instance["name"], categories=instance["categories"]))
        
        # concatenateFiles(config["tmp_dir"], 'roles/kubernetes/tasks/main.yaml')
        # cleanTmpDir(config["tmp_dir"])
        
    # if "jupyter" in config:
    
        # shutil.copyfile("default-ansible-vars", install_dir + "/roles/jupyter/vars/main.yaml")
        
        # # write the playbook that installs Jupyter and opens port 8000 in the director security group
        # os.system('ansible-playbook -ilocalhost, install-jupyter-pb.yaml')
    
    printBanner('Run the playbooks')
    
    #os.system('ansible-playbook -vv site.yaml')
    
    printBanner('Done')
    
    print("Script time: %s" % (datetime.datetime.now() - begin_time))
                