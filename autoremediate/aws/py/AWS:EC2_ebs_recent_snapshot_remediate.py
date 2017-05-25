## 
## Lambda function to automatically remediate Evident signature: AWS:EC2 - ebs_recent_snapshot_check
##
## PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
## Copyright (c) 2016 Evident.io, Inc., All Rights Reserved
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
        volume = metadata['attributes']['data']['resource_id']
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
