## 
## Lambda function to automatically remediate Evident signatue: AWS:EC2 - security_group_global_inbound_port_check
##
## PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
## Copyright (c) 2016 Evident.io, Inc., All Rights Reserved
##
## ---------------------------------------------------------------------------------
## Use lambda policy: ../policies/AWS_EC2_security_group_global_inbound_policy.json
## ---------------------------------------------------------------------------------
##

from __future__ import print_function

import json
import re
import boto3
import sys

# Options
#
admin_port_list  = [ 'tcp-22', 'tcp-23', 'tcp-3389' ]
global_cidr_list = [ '0.0.0.0/0', '::/0' ]

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
    except Exception as e:
        print('=> No security group to evaluate.')
    else:
        print ("=> Autoremediating security group " + sg_id, "in region " + region)
        results = auto_remediate(region, sg_id)


def auto_remediate(region, sg_id):
    """
    Auto-Remediate - Removes Admin ports from the offending security group
    """

    ec2 = boto3.client('ec2',region_name=region)

    ip_perms = ec2.describe_security_groups(GroupIds=[ sg_id, ])['SecurityGroups'][0]['IpPermissions']

    for ip_perm in ip_perms:
        from_port = ip_perm['FromPort']
        to_port = ip_perm['ToPort']
        ip_protocol = ip_perm['IpProtocol']

        for ip_range in ip_perm['IpRanges']:
            cidr_ip = ip_range['CidrIp']

            for admin_port in admin_port_list:
                proto = re.split('-', admin_port)[0]; port = re.split('-', admin_port)[1]
                find_port='true' if from_port <= port <= to_port else 'false'
                if cidr_ip in global_cidr_list and ip_protocol.lower() == proto and find_port == 'true':

                    try:
                        ec2.revoke_security_group_ingress(GroupId=sg_id, IpProtocol=ip_protocol, FromPort=from_port, ToPort=to_port, CidrIp=cidr_ip)
                    except Exception as e:
                        print('=> Error: ', str(e.message))
                    else:
                        print("=> Revoked rule permitting %s/%d-%d from %s" % (ip_protocol, from_port, to_port, sg_id))

    return None

