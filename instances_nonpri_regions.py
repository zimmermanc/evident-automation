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

# Requirements
#
# python v3
# boto3
# valid AWS config/profile -> ~/.aws/credentials

# AWS permissions
#
# ec2.describe_instances
# ec2.describe_images
# ec2.create_image
# ec2.terminate_instances 

# Settings
#
PROFILE = 'demolicious'  # AWS profile
PREFIX  = 'backup-'      # AMI name = 'PREFIX + instance_id'
REGIONS = ['eu-west-1', 'ap-northeast-1']

import boto3
import botocore
import sys
import json


def get_instances(ec2):
    """ Create a list of ec2 instances """

    instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': [ 'running','stopped' ]}])

    instance_list = []
    if instances['Reservations']:
        for i in instances['Reservations']:
            instance_id = i['Instances'][0]['InstanceId']
            instance_list.append(instance_id)
    
    return instance_list


def create_images(ec2, instance_list, region):
    """ Create a backup image (AMI) for each ec2 instance """

    waiter = ec2.get_waiter('image_available')

    image_list = []
    if instance_list:
        for i in instance_list:
            try:
                image_id = ec2.create_image(InstanceId=i, Name=PREFIX + i)['ImageId']
            except:
                pass
            else:
                print('Creating image %s for ec2 instance %s in region %s..' % (image_id, i, region))
                image_list.append(image_id)

        if image_list:
            waiter.wait(ImageIds=image_list)

    return


def kill_instances(ec2, instance_list, region):
    """ Terminate each ec2 instance with a backup AMI """

    if instance_list:
        print('Attempting to terminate ec2 instances in region %s..' % (region))
        for i in instance_list:
            ami = ec2.describe_images(Filters=[{'Name': 'name','Values': [PREFIX + i]}])['Images']
            if ami:
                try:
                    response = ec2.terminate_instances(InstanceIds=[i])
                except Exception as e:
                    print(e)
                else:
                    print(json.dumps(response['TerminatingInstances'], indent=4))

    return


def main():
    """ Do the work """

    try:
        s = boto3.Session(profile_name=PROFILE)
    except botocore.exceptions.ProfileNotFound as e:
        print(e)
        sys.exit(1)

    for r in REGIONS:
        ec2 = s.client('ec2', region_name=r)
        instance_list = get_instances(ec2)

        create_images(ec2, instance_list, r)
        kill_instances(ec2, instance_list, r)


if __name__ == "__main__":

  main()
