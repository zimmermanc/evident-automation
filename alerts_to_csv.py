from __future__ import print_function
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from hashlib import sha1

import uuid
import pycurl
import json
import md5
import base64
import cStringIO
import hmac
import time
import certifi

#=== Description ===
# Version 1.5
#
# Output the latest alerts into a CSV file.
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. (Optional) Enter which attributes you want to output. The attribute name can be anything from:
# a. Alert (http://api-docs.evident.io/#attributes)
# b. Signature (http://api-docs.evident.io/#attributes112)
# c. External Account (http://api-docs.evident.io/?json#attributes66)
# d. Team (http://api-docs.evident.io/?json#attributes170)
# e. Sub-organization (http://api-docs.evident.io/?json#attributes147)
# f. Organization (http://api-docs.evident.io/?json#attributes79)
# g. Region (http://api-docs.evident.io/?json#attributes85)
# h. Service (http://api-docs.evident.io/?json#attributes108)
# i. Suppression (http://api-docs.evident.io/?json#suppressions-attributes)
# j. Metadata (http://api-docs.evident.io/#attributes75)
#  WARNING: Metadata retrieval will require an API call per alert, meaning this would substantially increase
#           the amount of time required for the script to run. 
# Note: See example for formatting
# 3. (Optional) Modify the CSV parameters
# 4. (Optional) Specify the specific External Accounts you want to export.
# 5. (Optional) Specify the specific alert statuses that you want to export.
#
#=== End Description ===

#=== Configuration ===

# ESP API Access Key Credentials

public = <public key>
secret = <secret key>

# Export alerts for the following external accounts.  If none are specified, all external accounts will be exported.
# Accounts you don't have access to will be omitted.
# Example: EXTERNAL_ACCOUNT_IDS = ['1', '2']
EXTERNAL_ACCOUNT_IDS = []

# Alert status to query for.  If none are specified, alerts of all status will be exported.
# Valid values: 'info', 'pass', 'fail', 'warn', 'error'
STATUS = ['warn', 'fail']

# Alert attributes to output
ATTRIBUTES = ['alert.id', 'alert.created_at', 'alert.ended_at', 'signature.name', 'alert.status', 'region.code', 'organization.name', 'sub_organization.name', 'team.name', 'external_account.name', 'signature.identifier', 'alert.risk_level', 'service.name', 'signature.description', 'signature.resolution', 'suppression.id', 'suppression.created_at', 'suppression.reason', 'alert.resource'  ]

# CSV file parameters
DELIMITER = ','
CSV_FILENAME = 'alerts.csv'
OUTPUT_TO_CSV = True

#=== End Configuration ===

#=== Helper Methods ===

def call_api(action, url, data, count = 0):
    # Construct ESP API URL
    ev_create_url = 'https://api.evident.io%s' % (url)
    
    # Create md5 hash of body
    m = md5.new()
    m.update(data.encode('utf-8'))
    data_hash = base64.b64encode(m.digest())
    #print(data_hash)
    
    # Find Time
    now = datetime.now()
    stamp = mktime(now.timetuple())
    #print(format_date_time(stamp))
    
    # Create Authorization Header
    canonical = '%s,application/vnd.api+json,%s,%s,%s' % (action, data_hash, url, format_date_time(stamp))
    #print(canonical)
    
    hashed = hmac.new(secret, canonical, sha1)
    auth = hashed.digest().encode("base64").rstrip('\n')
    
    # Create Curl request
    buf = cStringIO.StringIO()
    c = pycurl.Curl()
    c.setopt(pycurl.CAINFO, certifi.where())
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
    elif action == 'DELETE':
        c.setopt(c.CUSTOMREQUEST, 'DELETE')
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
# Should return '1003'
def get_id(link):
    a = link.split("/")
    b = a[len(a) - 1].split(".")
    return b[0]

# Retrieve list of items of specified type
def get_items(item_type):
    items = {}
    page_num = 1
    has_next = True
    while has_next:
        ev_create_url = '/api/v2/%s?page[number]=%d&page[size]=100' % (item_type, page_num)
        data = ''
        ev_response_json = call_api('GET', ev_create_url, data)
        if 'data' in ev_response_json:
            for item in ev_response_json['data']:
                item['attributes']['id'] = item['id']
                items[item['id']] = item
        page_num += 1
        has_next = ('next' in ev_response_json['links'])
        ev_response_json = call_api('GET', ev_create_url, data)
    return items

# Retrieve alert metadata
def get_metadata(alert_id):
    ev_create_url = '/api/v2/alerts/%s/metadata' % alert_id
    data = ''
    ev_response_json = call_api('GET', ev_create_url, data)
    if 'data' in ev_response_json:
        item = ev_response_json['data']
        item['attributes']['id'] = item['id']
        return item

# Retrieve latest alerts for given external account ID
def find_latest_alerts(external_account_id):
    data = ''
    ev_create_url = '/api/v2/reports?filter[external_account_id_eq]=%s' % external_account_id
    
    ev_response_json = call_api('GET', ev_create_url, data)
    for report in ev_response_json['data']:
        if 'status' in report['attributes'] and report['attributes']['status'] == 'complete':
            alerts = []
            page_num = 1
            has_next = True
            while has_next:
                print(' Getting page %d' % page_num)
                ev_create_url = '/api/v2/reports/%s/alerts.json?page[number]=%d&page[size]=100' % (report['id'], page_num)
                for status in STATUS:
                    ev_create_url += '&filter[status_in][]=%s' % status
                
                ev_response_json = call_api('GET', ev_create_url, data)
                alerts += ev_response_json['data']
                page_num += 1
                has_next = ('next' in ev_response_json['links'])
                
            # Retrieve suppressed alerts
            page_num = 1
            has_next = True
            while has_next:
                print(' Getting page %d' % page_num)
                ev_create_url = '/api/v2/reports/%s/alerts.json?page[number]=%d&page[size]=100&filter[suppressed]=true' % (report['id'], page_num)
                ev_response_json = call_api('GET', ev_create_url, data)
                alerts += ev_response_json['data']
                page_num += 1
                has_next = ('next' in ev_response_json['links'])
                
            return alerts

def get_signature_id(alert):
    if alert['relationships']['signature']['links']['related'] is not None:
        return get_id(alert['relationships']['signature']['links']['related'])
    elif alert['relationships']['custom_signature']['links']['related'] is not None:
        return get_id(alert['relationships']['custom_signature']['links']['related'])
    return -1
        
def is_standard_sig(alert):
    if alert['relationships']['signature']['links']['related'] is not None:
        return True
    elif alert['relationships']['custom_signature']['links']['related'] is not None:
        return False
    return -1

# Retrieve and process all external accounts
def get_all_alerts():
    latest_alerts = []
    page_num = 1
    has_next = True
    while has_next:
        data = ''
        ev_create_url = '/api/v2/external_accounts?page[number]=%d&page[size]=100' % page_num
        ev_response_json = call_api('GET', ev_create_url, data)
        for external_account in ev_response_json['data']:
            if not EXTERNAL_ACCOUNT_IDS or external_account['id'] in EXTERNAL_ACCOUNT_IDS:
                print('Retrieving alerts for %s' % external_account['id'])
                latest_alerts += find_latest_alerts(external_account['id'])
        page_num += 1
        has_next = ('next' in ev_response_json['links'])
        ev_response_json = call_api('GET', ev_create_url, data)
    return latest_alerts

def get_output():
    print('Retrieving standard signatures')
    signatures = get_items('signatures')

    print('Retrieving custom signatures')
    custom_signatures = get_items('custom_signatures')
    
    print('Retrieving services')
    services = get_items('services')
    
    print('Retrieving regions')
    regions = get_items('regions')

    print('Retrieving external accounts')
    external_accounts = get_items('external_accounts')
    
    print('Retrieving organizations')
    organizations = get_items('organizations')
    
    print('Retrieving sub-organizations')
    sub_organizations = get_items('sub_organizations')
    
    print('Retrieving teams')
    teams = get_items('teams')
    
    print('Retrieving suppressions')
    suppressions = get_items('suppressions')
    
    latest_alerts = get_all_alerts()

    # Generate string in CSV format
    output = ''
    for attribute in ATTRIBUTES:
        output += attribute + ','
    output = output[:(len(output) - 1)] + '\n'

    for alert in latest_alerts: 
        metadata = None
        
        if is_standard_sig(alert):
            signature = signatures[get_signature_id(alert)]
            service = services[get_id(signature['relationships']['service']['links']['related'])]
        else:
            signature = custom_signatures[get_signature_id(alert)]
            service = None
        
        region = regions[get_id(alert['relationships']['region']['links']['related'])]
        external_account = external_accounts[get_id(alert['relationships']['external_account']['links']['related'])]
        if alert['relationships']['suppression']['links']['related'] is not None:
            suppression = suppressions[get_id(alert['relationships']['suppression']['links']['related'])]
        else:
            suppression = None

        for attribute in ATTRIBUTES:
            att_type, attribute = attribute.split(".")
            value = ''
            if att_type == 'alert' and attribute in alert and alert[attribute] is not None:
                value = alert[attribute]
            elif att_type == 'alert' and attribute in alert['attributes'] and alert['attributes'][attribute] is not None:
                value = alert['attributes'][attribute]
            elif att_type == 'signature' and attribute in signature['attributes'] and signature['attributes'][attribute] is not None:
                value = signature['attributes'][attribute]
            elif att_type == 'region' and attribute in region['attributes'] and region['attributes'][attribute] is not None:
                value = region['attributes'][attribute]
            elif att_type == 'service' and service is not None and attribute in service['attributes'] and service['attributes'][attribute] is not None:
                value = service['attributes'][attribute]
            elif att_type == 'external_account' and attribute in external_account['attributes'] and external_account['attributes'][attribute] is not None:
                value = external_account['attributes'][attribute]
            elif att_type == 'organization' and attribute in external_account['attributes'] and external_account['attributes'][attribute] is not None:
                organization_id = get_id(external_account['relationships']['organization']['links']['related'])
                organization = organizations[organization_id]
                value = organization['attributes'][attribute]
            elif att_type == 'sub_organization' and attribute in external_account['attributes'] and external_account['attributes'][attribute] is not None:
                sub_organization_id = get_id(external_account['relationships']['sub_organization']['links']['related'])
                sub_organization = sub_organizations[sub_organization_id]
                value = sub_organization['attributes'][attribute]
            elif att_type == 'team' and attribute in external_account['attributes'] and external_account['attributes'][attribute] is not None:
                team_id = get_id(external_account['relationships']['team']['links']['related'])
                team = teams[team_id]
                value = team['attributes'][attribute]
            elif att_type == 'suppression' and suppression is not None and attribute in suppression['attributes'] and suppression['attributes'][attribute] is not None:
                value = suppression['attributes'][attribute]
            elif att_type == 'metadata':
                if metadata is None:
                    metadata = get_metadata(alert['id'])
                if attribute == 'data':
                    value = json.dumps(metadata['attributes'][attribute])
                else:
                    value = metadata['attributes'][attribute]
            
            # Remove non-ASCII symbols
            # Surround values with , in double quotes if it doesn't have that already
            # Escape any double quotes
            value = value.encode('ascii',errors='ignore')
            if ',' in value and value[:1] != '"':
                value = '"' + value.encode('ascii',errors='ignore').replace('"', '""') + '"'
            else:
                value = value.replace('\\"', '""')
            output += value + DELIMITER
        output = output[:(len(output) - 1)] + '\n'
            
    return output

def save_to_file(output):
    with open(CSV_FILENAME, 'w') as f: 
        f.write(output) 
        
#=== End Helper Methods ===
        
# === Main Script ===

output = get_output()
#print(output)

if OUTPUT_TO_CSV:
    save_to_file(output)

# === End Main Script ===
