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
# Takes a snapshot (image) of ec2 instances in non-primary regions
# then attempts to terminate those ec2 instances
# ---
#

from __future__ import print_function

import boto3
import sys
import json
import re

PREFIX = 'backup-'    # AMI name = 'PREFIX + instance_id'


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
        instance_id = metadata['attributes']['data']['resource_id']
    except:
        print('=> No instances to evaluate.')
    else:
        print ('=> Autoremediating instance ' + instance_id, 'in region ' + region)
        results = auto_remediate(region, instance_id)


def auto_remediate(region, instance_id):
    """
    Auto-Remediate
    """

    ec2 = boto3.client('ec2', region_name=region)

    create_image(ec2, instance_id, region)
    kill_instance(ec2, instance_id, region)

    return


def create_image(ec2, instance_id, region):
    """ Create a backup image (AMI) for the instance """

    waiter = ec2.get_waiter('image_available')
    image_list = []

    try:
        image_id = ec2.create_image(InstanceId=instance_id, Name=PREFIX + instance_id)['ImageId']
    except:
        pass
    else:
        print('=> Creating image %s for instance %s in region %s..' % (image_id, instance_id, region))
        image_list.append(image_id)

    if image_list:
        waiter.wait(ImageIds=image_list)

    return


def kill_instance(ec2, instance_id, region):
    """ Terminate instance with a backup AMI """

    ami = ec2.describe_images(Filters=[{'Name': 'name','Values': [PREFIX + instance_id]}])['Images']
    if ami:
        try:
            response = ec2.terminate_instances(InstanceIds=[instance_id])
        except Exception as e:
            print(e)
        else:
            print(response['TerminatingInstances'])

    return
