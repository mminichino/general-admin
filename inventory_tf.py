#!/usr/bin/env python

'''
Dynamic inventory script for db-host-prep
'''

import os
import sys
import argparse
import json
import socket
import dns.resolver
import dns.reversename
import subprocess

class dynamicInventory(object):

    def __init__(self):
        self.inventory = {}

        self.parse_args()

        if "TERRAFORM_PATH" not in os.environ:
             self.inventory = self.empty_inventory()
        elif self.args.list:
            self.terraformPath = os.environ['TERRAFORM_PATH']
            self.inventory = self.lab_inventory()
        elif self.args.host:
            self.inventory = self.empty_hostvars()
        else:
            self.inventory = self.empty_hostvars()

        print(json.dumps(self.inventory))

    def lab_inventory(self):
        inventoryJson = {}
        inventoryJson['lab'] = {"hosts": [], "vars": {}}
        inventoryJson['_meta'] = {"hostvars": {}}
        hostname = socket.gethostname()
        homeDir = os.environ['HOME']
        dnsKeyFile = homeDir + "/.dns/dns.key"
        runCommand = []

        try:
            ip_result = dns.resolver.query(hostname, 'A')
            arpa_result = dns.reversename.from_address(ip_result[0].to_text())
            fqdn_result = dns.resolver.query(arpa_result, 'PTR')
            host_fqdn = fqdn_result[0].to_text()
            domain_name = host_fqdn.split('.',1)[1].rstrip('.')

            inventoryJson['lab']['vars']['domain'] = domain_name
        except dns.resolver.NXDOMAIN:
            pass

        if os.path.exists(dnsKeyFile):
            try:
                with open(dnsKeyFile, 'r') as keyFile:
                    try:
                        keyData = json.load(keyFile)
                    except ValueError as e:
                        print("DNS key file ~/.dns/dns.key does not contain valid JSON data: %s" % str(e))
                        sys.exit(1)
                    if keyData['dnskey']:
                        inventoryJson['lab']['vars']['dnssecret'] = keyData['dnskey']
                    if keyData['keyname']:
                        inventoryJson['lab']['vars']['dnskey'] = keyData['keyname']
            except OSError as e:
                print("Could not read dns key file: %s" % str(e))
                sys.exit(1)

        runCommand.append('terraform')
        runCommand.append('-chdir=' + self.terraformPath)
        runCommand.append('output')
        runCommand.append('-json')
        runProccess = subprocess.Popen(runCommand, stdout=subprocess.PIPE)
        stdout_text = runProccess.stdout.read()
        stdout_json = stdout_text.decode('utf-8')

        output = json.loads(stdout_json)

        for key in output:
            if key.startswith('inventory'):
                for x in range(len(output[key]['value'])):
                    inventoryJson['lab']['hosts'].append(output[key]['value'][x])

        return inventoryJson

    def empty_hostvars(self):
        return {'_meta': {'hostvars': {}}}

    def empty_inventory(self):
        inventoryJson = {}
        inventoryJson['lab'] = {"hosts": [], "vars": {}}
        inventoryJson['_meta'] = {"hostvars": {}}
        return inventoryJson

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

def main():
    dynamicInventory()

if __name__ == '__main__':

    try:
        main()
    except SystemExit as e:
        if e.code == 0:
            os._exit(0)
        else:
            os._exit(e.code)
