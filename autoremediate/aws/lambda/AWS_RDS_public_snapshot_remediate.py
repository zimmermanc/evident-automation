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
## Lambda function to automatically remediate Evident signature: AWS:RDS - public_snapshot_check
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
