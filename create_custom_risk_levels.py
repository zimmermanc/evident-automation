from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from hashlib import sha1

import pycurl
import json
import md5
import base64
import cStringIO
import hmac
import time

#=== Description ===
# Update a list of External Accounts with the same set of Signature Custom Risk Levels.
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. Modify external_account_ids to include the list of External Accounts IDs that you want to update
# 3. Update identifier_to_risk_levels with Signature Identifier to Risk Level pairs 
#
# Limitions:
# - Currently, the script supports up to 200 standard signatures.  To retrieve more, update NUM_OF_SIGS variable.
# - Script will fail if a signature's risk level is customized to the default value.
#
#=== End Description ===

#=== Configuration ===

# ESP API Access Key Credentials
public = <public>
secret = <secret>

# List of External Accounts Ids to update
# If none are specified, then all external accounts will be updated
external_account_ids = [<id>, <id>, ...]

# List of Signature Identifier - Risk Level pairs to update
identifier_to_risk_levels = {}
identifier_to_risk_levels['AWS:CONFIG-001'] = 'high'
identifier_to_risk_levels['AWS:VPC-001'] = 'low'
identifier_to_risk_levels['AWS:VPC-006'] = 'low'
identifier_to_risk_levels['AZU:NSG-001'] = 'low'

# Number of signatures to retrieve
NUM_OF_SIGS = 3 # In hundreds

# DO NOT MODIFY
sig_prefix_to_provider = {}
sig_prefix_to_provider['AWS'] = 'amazon'
sig_prefix_to_provider['AZU'] = 'azure'

#=== End Configuration ===

#=== Helper Methods ===
# Process API requests
def call_api(action, url, data, count = 0):
    # Construct ESP API URL
    ev_create_url = 'https://api.evident.io%s' % (url)
    
    # Create md5 hash of body
    m = md5.new()
    m.update(data.encode('utf-8'))
    data_hash = base64.b64encode(m.digest())
    
    # Find Time
    now = datetime.now()
    stamp = mktime(now.timetuple())
    
    # Create Authorization Header
    canonical = '%s,application/vnd.api+json,%s,%s,%s' % (action, data_hash, url, format_date_time(stamp))

    hashed = hmac.new(secret, canonical, sha1)
    auth = hashed.digest().encode("base64").rstrip('\n')
    
    # Create Curl request
    buf = cStringIO.StringIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(ev_create_url))
    c.setopt(pycurl.HTTPHEADER, [
        'Date: %s' % format_date_time(stamp),
        'Content-MD5: %s' % data_hash,
        'Content-Type: application/vnd.api+json', 
        'Accept: application/vnd.api+json',
        'Authorization: APIAuth %s:%s' % (public, auth)])
    c.setopt(c.WRITEFUNCTION, buf.write)
    
    if action == 'POST':
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, data)
    elif action == 'PATCH':
        c.setopt(c.CUSTOMREQUEST, 'PATCH')
        c.setopt(pycurl.POSTFIELDS, data)
    c.perform()
    ev_response = buf.getvalue()
    buf.close()
    c.close()
    ev_response_json = json.loads(ev_response)
    
    # Handle rate-limit exceptions
    if 'errors' in ev_response_json:
        for error in ev_response_json['errors']:
            print(error)
            if int(error['status']) == 429:
                if count < 5:
                    # Wait 60 seconds for every retry
                    time.sleep(60 * (count + 1))
                    count += 1
                    print("retry - %s" % count)
                    return call_api(action, url, data, count)
                else:
                    # Give-up after 5 retries
                    return false
            else:
                # Throw Exception and end script if any other error occurs
                raise Exception('%d - %s' % (int(error['status']), error['title']))
    
    return ev_response_json

# Get id from relationship link
# Example: http://test.host/api/v2/signatures/1003.json
# Should return 1003
def get_id(link):
    a = link.split("/")
    b = a[len(a) - 1].split(".")
    return int(b[0])

#=== End Helper Methods ===

#=== Main Script ===

# Variables
num_of_fails = 0
identifier_to_sig_id = {}

# Retrieve list of Signatures
signature_list = []
for x in xrange(NUM_OF_SIGS):
    ev_create_url = '/api/v2/signatures?page[number]=%d&page[size]=100' % (x + 1)
    data = ''
    ev_response_json = call_api('GET', ev_create_url, data)
    if 'data' in ev_response_json:
        signature_list += ev_response_json['data']
        
# Generate hash of Signature Identifier to Signature ID
for sig in signature_list:
    identifier_to_sig_id[sig['attributes']['identifier']] = int(sig['id'])
    
# Retrieve accounts and account types
account_id_to_provider = {}
if not external_account_ids:
    ev_create_url = '/api/v2/external_accounts?page[size]=100'
    data = ''
    ev_response_json = call_api('GET', ev_create_url, data)
    for external_accounts in ev_response_json['data']:
        external_account_ids.append(int(external_accounts['id']))
        account_id_to_provider[int(external_accounts['id'])] = external_accounts['attributes']['provider']
else:
    external_accounts = []
    for external_account_id in external_account_ids:
        ev_create_url = '/api/v2/external_accounts/%d' % external_account_id
        data = ''
        ev_response_json = call_api('GET', ev_create_url, data)
        external_account = ev_response_json['data']
        account_id_to_provider[external_account_id] = external_account['attributes']['provider']
        
# Iterate for each External Account
for external_account_id in external_account_ids:
    print("Modify risk levels for account %d" % external_account_id)

    # Retrieve list of Signature Custom Risk Levels
    scrl_list = []
    for x in xrange(NUM_OF_SIGS):
        ev_create_url = '/api/v2/external_accounts/%d/signature_custom_risk_levels?page[number]=%d&page[size]=100' % (external_account_id, (x+1))
        data = ''
        ev_response_json = call_api('GET', ev_create_url, data)
        if 'data' in ev_response_json:
            scrl_list += ev_response_json['data']

    # Generate hash of Signature ID to Signature Custom Risk Level ID pair
    sig_ids = []
    for scrl in scrl_list:
        if scrl['attributes']['custom_risk_level'] is not None:
            sig_ids.append(int(scrl['id']))

    # Iterate for each Signature Identifier to Risk Level pair
    for identifier in identifier_to_risk_levels:
        # Custom Risk Level already set, need to update
        sig_id = identifier_to_sig_id[identifier]
        if sig_id in sig_ids:
            # Construct body
            data = json.dumps({
                'data': {
                    'type': 'signature_custom_risk_levels',
                    'attributes': { 
                        'risk_level': identifier_to_risk_levels[identifier]
                    }
                }
            })
            ev_create_url = '/api/v2/external_accounts/%d/signature_custom_risk_levels/%d' % (external_account_id, sig_id)
            ev_response_json = call_api('PATCH', ev_create_url, data)
            if 'data' in ev_response_json:
                print('update custom risk level: %s to %s' % (identifier, identifier_to_risk_levels[identifier]))
            else:
                num_of_fails += 1
                print('failed to update custom risk level: %s to %s' % (identifier, identifier_to_risk_levels[identifier]))
        # Custom Risk Level doesn't exist, need to create
        elif sig_prefix_to_provider[identifier[:3]] == account_id_to_provider[external_account_id]:
            # Construct body
            data = json.dumps({
                'data': {
                    'type': 'signature_custom_risk_levels',
                    'attributes': {
                        'signature_id': identifier_to_sig_id[identifier],
                        'risk_level': identifier_to_risk_levels[identifier]
                    }
                }
            })
            ev_create_url = '/api/v2/external_accounts/%d/signature_custom_risk_levels' % external_account_id
            ev_response_json = call_api('POST', ev_create_url, data)
            if 'data' in ev_response_json:
                print('create custom risk level: %s to %s' % (identifier, identifier_to_risk_levels[identifier]))
            else:
                num_of_fails += 1
                print('failed to create custom risk level: %s to %s' % (identifier, identifier_to_risk_levels[identifier]))
        # else: Account type doesn't match sig type, so skip
            

if num_of_fails == 0:
    print('Completed')
else:
    print('Completed, but %d signatures failed to update' % num_of_fails)

#=== End Main Script ===
