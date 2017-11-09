# Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
# 
#   Evident.io shall retain all ownership of all right, title and interest in and to 
#   the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
#   including (a) all information and technology capable of general application to Evident.io's
#   customers; and (b) any works created by Evident.io prior to its commencement of any
#   Services for Customer.
# 
# Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
#   Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
#   use, copy, configure and translate any Deliverable solely for internal business operations
#   of the Customer as they relate to the Evident.io platform and products, and always
#   subject to Evident.io's underlying intellectual property rights.
# 
# IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
#   INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
#   THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
#   THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
#   EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
#   OR MODIFICATIONS.
# 
# ---
# 
# Lambda function to automatically remediate Evident signatue:
# * AWS:EC2-031 Unused Security Groups
#
# ---------------------------------------------------------------------------------
# Use lambda policy: ../policies/AWS_EC2_unused_security_group_policy.json
# ---------------------------------------------------------------------------------
#

from __future__ import print_function

import json
import re
import boto3

print('=> Loading function')

def lambda_handler(event, context):
    try:
        message = event['Records'][0]['Sns']['Message']
    except KeyError:
        try:
            message = event['Records'][0]['Sns']
        except KeyError:
            print('=> KeyError: No SNS key found.')
            return
        else:
            alert = message
    else:
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
        sg_id = metadata['attributes']['data']['details']['securityGroup']['groupId']
        #sg_id = metadata['attributes']['data']['resource_id']
    except:
        print("=> No security group to evaluate.")
    else:
        print ("=> Autoremediating security group {} in region {}.. ".format(sg_id, region))
        results = auto_remediate(region, sg_id)

        print(results)


def auto_remediate(region, sg_id):
    """
    Auto-Remediate - Delete unused security groups
    """

    ec2 = boto3.client('ec2', region_name=region)

    lambda_check = lambda_sg(region, sg_id)
    if lambda_check != 'false':
        return "=> Security group, {} is tied to a Lambda function. Skipping..".format(sg_id)

    try:
        ec2.delete_security_group(GroupId=sg_id)
    except Exception as e:
        results = str(e)
    else:
        results = "=> Removed unused security group, {}.".format(sg_id)

    return results


def lambda_sg(region, sg_id):
    """
    Check - Security group tied to a Lambda function?
    """

    lam = boto3.client('lambda', region_name=region)

    lambda_check = 'false'
    for func in lam.list_functions()['Functions']:
        if lambda_check == 'true':
            return lambda_check
        try:
            vpc_config = func['VpcConfig']
        except:
            continue
        else:
            security_groups = vpc_config['SecurityGroupIds']
            for sg in security_groups:
                if sg == sg_id:
                    lambda_check = 'true'

    return lambda_check
