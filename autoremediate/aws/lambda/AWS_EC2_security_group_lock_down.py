## Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
## 
##   Evident.io shall retain all ownership of all right, title and interest in and to 
##   the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
##   including (a) all information and technology capable of general application to Evident.io's
##   customers; and (b) any works created by Evident.io prior to its commencement of any
##   Services for Customer.
## 
## Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
##   Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
##   use, copy, configure and translate any Deliverable solely for internal business operations
##   of the Customer as they relate to the Evident.io platform and products, and always
##   subject to Evident.io's underlying intellectual property rights.
## 
## IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
##   INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
##   THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
##   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
## 
## EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
##   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
##   THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
##   EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
##   OR MODIFICATIONS.
## 
## ---
##
## Lambda function to automatically remediate Evident built-in signatues:
##
## EC2-009 MySQL (TCP Port 3306) Detected
## EC2-010 PostgreSQL (TCP Port 5432) Detected
## EC2-011 SQLServer (TCP Port 1433) Detected
## EC2-012 SQLServer (UDP Port 1434) Detected
## EC2-013 MSQL (TCP Port 4333) Detected
## EC2-014 VNC Listener (TCP Port 5500) Detected
## EC2-015 VNC Server (TCP Port 5900) Detected
## EC2-016 NetBIOS (UDP Port 137) Detected
## EC2-017 NetBIOS (UDP Port 138) Detected
## EC2-018 CIFS (UDP Port 445) Detected
## EC2-019 FTP (TCP Port 21) Detected
## EC2-020 FTP-Data (TCP Port 20) Detected
## EC2-021 SMTP (TCP Port 25) Detected
## EC2-022 (Ping) Access Detected
## EC2-023 DNS (UDP Port 53) Detected
## EC2-024 DNS (TCP Port 53) Detected
## EC2-040 Global permission is defined on a range of ports
##
## ---------------------------------------------------------------------------------
## Use lambda policy: ../policies/AWS_EC2_security_group_global_inbound_policy.json
## ---------------------------------------------------------------------------------
##

from __future__ import print_function

## Options
sig_port_list = [ 'tcp 3306', 'tcp 5432', 'tcp 1433', 'udp 1434', 'tcp 4333', 'tcp 5500', 'tcp 5900', 'udp 137', 'udp 138', 'udp 445', 'tcp 21', 'tcp 20', 'tcp 25', 'icmp -1', 'icmpv6 -1', 'udp 53', 'tcp 53' ]
#
global_cidr_list = [ '0.0.0.0/0', '::/0' ]

import json
import re
import boto3
import sys

print('=> Loading function')

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']

    alert = json.loads(message)
    status = alert['data']['attributes']['status']

    # If the signature didn't report a failure, exit..
    #
    if status != 'fail':
        print('=> Nothing to do.')
        exit()

    # Else, carry on..
    #
    included = alert['included']
    
    for i in included:
        type = i['type']
        if type == "regions":
            regions = i
        if type == "metadata":
            metadata = i
    
    region = re.sub('_','-',regions['attributes']['code'])

    try:
        sg_id = metadata['attributes']['data']['resource_id']
    except:
        print('=> No security group to evaluate.')
    else:
        print ("=> Autoremediating security group " + sg_id, "in region " + region)
        results = auto_remediate(region, sg_id)


def auto_remediate(region, sg_id):
    """
    Auto-Remediate - Removes Admin ports from the offending security group
    """

    ec2 = boto3.client('ec2', region_name=region)

    ip_perms = ec2.describe_security_groups(GroupIds=[ sg_id, ])['SecurityGroups'][0]['IpPermissions']
    for ip_perm in ip_perms:
        try:
            from_port   = ip_perm['FromPort']
        except:
            continue
        else:
            to_port     = ip_perm['ToPort']
            ip_protocol = ip_perm['IpProtocol']

        if ip_perm['IpRanges']:
            IpRanges = 'IpRanges'
            IpCidr   = 'CidrIp'
            for ip_range in ip_perm['IpRanges']:
                cidr_ip = ip_range['CidrIp']
                remove_sg_rule(ec2, sg_id, from_port, to_port, ip_protocol, cidr_ip, IpRanges, IpCidr)

        if ip_perm['Ipv6Ranges']:
            IpRanges = 'Ipv6Ranges'
            IpCidr   = 'CidrIpv6'
            for ip_range in ip_perm['Ipv6Ranges']:
                cidr_ip = ip_range['CidrIpv6']
                remove_sg_rule(ec2, sg_id, from_port, to_port, ip_protocol, cidr_ip, IpRanges, IpCidr)

    return None


def remove_sg_rule(ec2, sg_id, from_port, to_port, ip_protocol, cidr_ip, IpRanges, IpCidr):
    """
    Revoke security group ingress
    """

    for sig_port in sig_port_list:
        proto = re.split(' ', sig_port)[0]
        port  = re.split(' ', sig_port)[1]

        find_port='true' if from_port <= int(port) <= to_port else 'false'

        if cidr_ip in global_cidr_list and ip_protocol.lower() == proto and find_port == 'true':
            try:
                ec2.revoke_security_group_ingress(GroupId=sg_id, IpPermissions=[ {'IpProtocol': ip_protocol, 'FromPort': from_port, 'ToPort': to_port, IpRanges: [{ IpCidr: cidr_ip }] } ])
            except Exception as e:
                error = str(e.message)
                if 'rule does not exist' not in error:
                    print('=> Error: ', error)
            else:
                print("=> Revoked rule permitting %s/%d-%d with cidr %s from %s" % (ip_protocol, from_port, to_port, cidr_ip, sg_id))

