from __future__ import print_function
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from hashlib import sha1
from hashlib import md5

import sys
import uuid
import requests
import json
import base64
import io
import hmac
import time
import certifi
import codecs
import warnings
warnings.filterwarnings("ignore")

#=== Description ===
# Disable signatures AWS:RDS-011 and AWS:RDS-012 for all accounts.
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. Add external accounts that you DON'T want to disable sigantures
# 3. (Advanced) Modify the list of signatures you want to disable
#
#=== End Description ===

#=== Configuration ===

# ESP API Access Key Credentials
public = <public>
secret = <secret>

# Excluded External Accounts
# Add the IDs that you want to exclude
# example: excluded = ['1234', '2345']
excluded = []

# DO NOT MODIFY
signatures = [
    {'id': '205', 'provider': 'amazon'}, # AWS:RDS-011
    {'id': '208', 'provider': 'amazon'}  # AWS:RDS-012
]

#=== End Configuration ===

#=== End Configuration ===

#=== Helper Methods ===
# Process API requests
def call_api(action, url, data, count = 0):
    # Construct ESP API URL
    ev_create_url = 'https://api.evident.io%s' % (url)
    
    # Create md5 hash of body
    hex = md5(data.encode('UTF-8')).hexdigest()
    data_hash = codecs.encode(codecs.decode(hex, 'hex'),
                         'base64').decode().rstrip('\n')
    
    # Find Time
    now = datetime.now()
    stamp = mktime(now.timetuple())
    dated = format_date_time(stamp)
    
    # Create Authorization Header
    canonical = '%s,application/vnd.api+json,%s,%s,%s' % (action, data_hash, url, dated)
    key_bytes= bytes(secret, 'UTF-8')
    data_bytes= bytes(canonical, 'UTF-8')

    hashed = hmac.new(key_bytes, data_bytes, sha1)
    auth = str(base64.b64encode(hashed.digest()), 'UTF-8')
    headers = {'Date': '%s' % dated,
               'Content-MD5': '%s' % data_hash,
               'Content-Type': 'application/vnd.api+json',
               'Accept': 'application/vnd.api+json',
               'Authorization': 'APIAuth %s:%s' % (public, auth)}
    
    r = requests.Request(action, ev_create_url, data=data, headers=headers)
    p = r.prepare()
    s = requests.Session()
    ask = s.send(p, timeout=10, verify=False)
    ev_response_json = ask.json()
    
    # Handle rate-limit exceptions
    if 'errors' in ev_response_json:
        for error in ev_response_json['errors']:
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
            elif int(error['status']) == 422:
                return '422'
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

# Check if script should run
# Should NOT run if authenticated user has Evident role
def can_proceed():
    data = ''
    ev_create_url = '/api/v2/organizations'
    ev_response_json = call_api('GET', ev_create_url, data)

    if len(ev_response_json['data']) > 1:
        print("Do NOT run this with Evident role user.")
        sys.exit()

#=== End Helper Methods ===

#=== Main Script ===
can_proceed()

# Retrieve list of External Accounts
account_ids = []
data = ''
page_num = 1
has_next = True
while has_next:
    ev_create_url = '/api/v2/external_accounts?page[number]=%d&page[size]=100' % page_num
    ev_response_json = call_api('GET', ev_create_url, data)
    for account in ev_response_json['data']:
        if 'id' in account and account['id'] not in excluded:
            for signature in signatures:    
                if account['attributes']['provider'] == signature['provider']:
                    data = json.dumps({
                        'data': {
                            'type': 'disabled_signature',
                            'attributes': {
                                'signature_id': signature['id']
                            }
                        }
                    })
                    ev_create_url2 = '/api/v2/external_accounts/%s/disabled_signatures' % account['id']
                    ev_response_json2 = call_api('POST', ev_create_url2, data)
                    if ev_response_json2 != '422':
                        print("Disabled Signature %s on account %s" % (signature['id'], account['id'])) 
                    else:
                        print("Signature %s was already disabled on account %s" % (signature['id'], account['id'])) 

    page_num += 1
    has_next = ('next' in ev_response_json['links'])

#=== End Main Script ===
