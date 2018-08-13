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
## Lambda function to automatically remediate Evident signatue:
##
## AWS:EC2 - public_ami_remediate
##
## ---------------------------------------------------------------------------------
## Use lambda policy: ../policies/AWS_EC2_public_ami_remediate_policy.json
## ---------------------------------------------------------------------------------
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
        img_id = alert['data']['attributes']['resource']
    except:
        print('=> No AMI to evaluate.')
    else:
        print ("=> Autoremediating public AMI: " + img_id, "in region " + region)
        results = auto_remediate(region, img_id)


def auto_remediate(region, img_id):
    """
    Auto-Remediate - make public AMIs private
    """

    ec2 = boto3.resource('ec2', region_name=region)
    image = ec2.Image(img_id)

    # Is Image Public? Verify first before remediating...
    response = image.describe_attribute(Attribute='launchPermission', DryRun=False)
    launch_permissions = response['LaunchPermissions']

    if launch_permissions == [{'Group': 'all'}]:
        print('=> Auto-remediating public AMI...')
        results = set_ami_to_private(image)

    return None


def set_ami_to_private(image):
    """
    Toggle the AMI to private from public by removing 
    {'Group': 'all'} from AMI's LaunchPermissions
    """

    response = image.modify_attribute(
        Attribute = 'launchPermission',
        LaunchPermission = {
            'Remove': [{'Group': 'all'}]
        },
        DryRun = False
    )

