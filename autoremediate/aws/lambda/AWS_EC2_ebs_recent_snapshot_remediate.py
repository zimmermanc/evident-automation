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
## Lambda function to automatically remediate Evident signature: AWS:EC2 - ebs_recent_snapshot_check
##

from __future__ import print_function

import json
import re
import boto3
import sys
from datetime import datetime
from datetime import date

# Options
#
snapshot_age = 15

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
        volume = alert['data']['attributes']['resource']
    except Exception as e:
        print('=> No EBS Volumes to evaluate.')
    else:
        print ('=> Autoremediating EBS Volume ' + volume, 'in region ' + region)
        results = auto_remediate(region, volume)

        print ('=> Snapshot Results: ', results)


def auto_remediate(region, volume):
    """
    Auto-Remediate - Creates a Volume Snapshot
    """

    snapshot_needed = get_snapshot(region, volume)
    if snapshot_needed != 'true':
        return 'No snapshot required for volume ' + volume

    ec2 = boto3.client('ec2', region_name=region)
    try:
        results = ec2.create_snapshot(VolumeId=volume, Description='Autoremediate snapshot')
    except Exception as e:
        results = str(e.message)

    return results


def get_snapshot(region, volume):

    ec2 = boto3.client('ec2', region_name=region)
    snapshot = ec2.describe_snapshots(Filters=[{ 'Name': 'volume-id', 'Values': [ volume ] }])['Snapshots']

    if len(snapshot) > 0:
        print('=> Evaluating snapshot date/time...')
        snap_date = snapshot[0]['StartTime'].date()    # Snapshot creation date
        today = date.today()                           # Today's date
        delta = today - snap_date                      # The diff

        snapshot_needed = 'true' if (delta.days >= snapshot_age) else 'false'
    else:
        snapshot_needed = 'true'
    
    return snapshot_needed
