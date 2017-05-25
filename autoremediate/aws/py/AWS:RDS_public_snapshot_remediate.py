## 
## Lambda function to automatically remediate Evident signature: AWS:RDS - public_snapshot_check
##
## PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
## Copyright (c) 2016 Evident.io, Inc., All Rights Reserved
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
        db_snap_id = metadata['attributes']['data']['resource_id']
    except Exception as e:
        print('=> No RDS snapshot to evaluate.')
    else:
        print ('=> Autoremediating RDS snapshot ' + db_snap_id, 'in region ' + region)
        results = auto_remediate(region, db_snap_id)

        print ('=> RDS Snapshot Results: ', results)


def auto_remediate(region, db_snap_id):
    """
    Auto-Remediate - Remove RDS 'Public' Snapshot Permission
    """

    rds = boto3.client('rds', region_name=region)

    snap_attribs = rds.describe_db_snapshot_attributes(DBSnapshotIdentifier=db_snap_id)['DBSnapshotAttributesResult']['DBSnapshotAttributes']
    
    for attrib in snap_attribs:
        if attrib['AttributeName'] == 'restore':
            public = 'true' if (attrib['AttributeValues'][0] == 'all') else 'false'
        else:
            public = 'none'
            results = "Unable to find public attribute for " + db_snap_id

    if public == 'true':
        try:
            results = rds.modify_db_snapshot_attribute(DBSnapshotIdentifier=db_snap_id, AttributeName='restore', ValuesToRemove=[ 'all' ])
        except Exception as e:
            results = str(e.message)

    return results
