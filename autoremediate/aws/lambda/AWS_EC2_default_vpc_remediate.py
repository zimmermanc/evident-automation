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
## Lambda function to automatically remediate Evident signature:
##
## AWS:EC2 - default_vpc_check
##
## ---------------------------------------------------------------
## Use lambda policy: ../policies/AWS_EC2_default_vpc_policy.json
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
    if (status != 'fail' and status != 'warn'):
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
        vpc_id = alert['data']['attributes']['resource']
    except:
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
    except:
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

