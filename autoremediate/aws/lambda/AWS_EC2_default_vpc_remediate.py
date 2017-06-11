## 
## Lambda function to automatically remediate Evident signature: AWS:EC2 - default_vpc_check
##
## PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
## Copyright (c) 2016 Evident.io, Inc., All Rights Reserved
##
## ******************************* !! W A R N I N G !! ********************************
## *                 Deleting the default VPC is a permanent action.                  *
## *      You must contact AWS Support if you want to create a new default VPC.       *
## *                                                                                  *
## * See: https://aws.amazon.com/premiumsupport/knowledge-center/deleted-default-vpc/ *
## ************************************************************************************
##
## ---------------------------------------------------------------
## Use lambda policy: ../policies/AWS:EC2_default_vpc_policy.json
## ---------------------------------------------------------------
##

from __future__ import print_function

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
        vpc_id = metadata['attributes']['data']['resource_id']
    except Exception as e:
        print('=> No VPC to evaluate.')
    else:
        results = auto_remediate(region, vpc_id)

        print ('=> VPC Results: ', results)


def auto_remediate(region, vpc_id):
    """
    Auto-Remediate - Delete Default VPCs

    == Order of operation ==

    1.) Delete the internet-gateway
    2.) Delete subnets
    3.) Delete route-tables
    4.) Delete network access-lists
    5.) Delete security-groups
    6.) Delete the VPC 
    """

    ec2 = boto3.client('ec2', region_name=region)

    # Does the vpc_id exist?
    try:
      vpc = ec2.describe_vpcs(VpcIds=[ vpc_id ])
    except Exception as e:
      return vpc_id + ' in region ' + region + ' does not exist.'
    else:
      vpc = vpc['Vpcs'][0]['IsDefault']

    # Is vpc_id the default?
    if vpc != True:
      return vpc_id + ' in region ' + region + ' is not the default.'
    else:
      print ('=> Autoremediating default VPC ' + vpc_id, 'in region ' + region)

    # Are there any existing resources?  Since most resources attach an ENI, let's check..
    eni = ec2.describe_network_interfaces(Filters=[ {'Name': 'vpc-id', 'Values': [ vpc_id ]} ])['NetworkInterfaces']
    if eni:
      return vpc_id + ' in region ' + region + ' has existing resources.'

    # Do the work..
    remove_ingw(ec2, vpc_id)
    remove_subs(ec2, vpc_id)
    remove_rtbs(ec2, vpc_id)
    remove_acls(ec2, vpc_id)
    remove_sgps(ec2, vpc_id)

    try:
      ec2.delete_vpc(VpcId=vpc_id)
    except Exception as e:
      results = str(e.message)
    else:
      results = vpc_id + ' in region ' + region + ' has been deleted.'

    return results


def remove_ingw(ec2, vpc_id):
    """ Detach and delete the internet-gateway """

    igw = ec2.describe_internet_gateways(Filters=[ {'Name' : 'attachment.vpc-id', 'Values' : [ vpc_id ]} ])['InternetGateways']

    if igw:
      igw_id = igw[0]['InternetGatewayId']

      try:
        ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
      except Exception as e:
        print(str(e.message))

      try:
        ec2.delete_internet_gateway(InternetGatewayId=igw_id)
      except Exception as e:
        print(str(e.message))


def remove_subs(ec2, vpc_id):
    """ Delete the subnets """

    subs = ec2.describe_subnets(Filters=[{ 'Name' : 'vpc-id', 'Values' : [ vpc_id ]} ])['Subnets']

    if subs:
      for sub in subs:
        sub_id = sub['SubnetId']

        try:
          ec2.delete_subnet(SubnetId=sub_id)
        except Exception as e:
          print(str(e.message))


def remove_rtbs(ec2, vpc_id):
    """ Delete the route-tables """

    rtbs = ec2.describe_route_tables(Filters=[{ 'Name' : 'vpc-id', 'Values' : [ vpc_id ]} ])['RouteTables']

    if rtbs:
      for rtb in rtbs:
        main = 'false'
        for assoc in rtb['Associations']:
          main = assoc['Main']
        if main == True:
          continue
        rtb_id = rtb['RouteTableId']
        
        try:
          ec2.delete_route_table(RouteTableId=rtb_id)
        except Exception as e:
          print(str(e.message))


def remove_acls(ec2, vpc_id):
    """ Delete the network-access-lists """

    acls = ec2.describe_network_acls(Filters=[{ 'Name' : 'vpc-id', 'Values' : [ vpc_id ]} ])['NetworkAcls']

    if acls:
      for acl in acls:
        default = acl['IsDefault']
        if default == True:
          continue
        acl_id = acl['NetworkAclId']

        try:
          ec2.delete_network_acl(NetworkAclId=acl_id)
        except Exception as e:
          print(str(e.message))


def remove_sgps(ec2, vpc_id):
    """ Delete any security-groups """

    sgps = ec2.describe_security_groups(Filters=[{ 'Name' : 'vpc-id', 'Values' : [ vpc_id ]} ])['SecurityGroups']

    if sgps:
      for sgp in sgps:
        default = sgp['GroupName']
        if default == 'default':
          continue
        sg_id = sgp['GroupId']

        try:
          ec2.delete_security_group(GroupId=sg_id)
        except Exception as e:
          print(str(e.message))

