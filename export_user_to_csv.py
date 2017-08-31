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
import csv

#=== Description ===
# Export the list of users to a CSV file
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. Update CSV_FILENAME to the desired filename.
#    Default: users.csv
# 3. Update the list of user attributes to output
#    Supported: id, created_at, email, time_zone, first_name, last_name, phone, mfa_enabled, disable_daily_emails, updated_at, role
#    Default: first_name, last_name, email, role, created_at
#
# Limition:
# - Have not tested with more than 100 users.
#
#=== End Description ===

#=== Configuration ===

# ESP API Access Key Credentials
public = <public key>
secret = <secret key>

# Output filename
CSV_FILENAME = 'users.csv'

# List of attributes
attributes = ['first_name', 'last_name', 'email', 'role', 'created_at']

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

# Retrieve list of role names
def get_role_names():
    role_names = {}
    data = ''
    page_num = 1
    has_next = True
    while has_next:
        ev_create_url = '/api/v2/roles?page[number]=%d&page[size]=100' % page_num
        ev_response_json = call_api('GET', ev_create_url, data)
        if 'data' in ev_response_json:
            for role in ev_response_json['data']:
                role_names[str(role['id'])] = role['attributes']['name']

        page_num += 1
        has_next = ('next' in ev_response_json['links'])
        
    return role_names

#=== End Helper Methods ===

#=== Main Script ===
# Retrieve list of role names
role_names = get_role_names()

# Retrieve list of Users
users = []
data = ''
page_num = 1
has_next = True
while has_next:
    ev_create_url = '/api/v2/users?page[number]=%d&page[size]=100' % page_num
    ev_response_json = call_api('GET', ev_create_url, data)
    if 'data' in ev_response_json:
        users += ev_response_json['data']
    
    page_num += 1
    has_next = ('next' in ev_response_json['links'])
    
# Append roles attributes
for user in users:
    user['attributes']['role'] = role_names[str(get_id(user['relationships']['role']['links']['related']))]
    
# Print Users to CSV
with open(CSV_FILENAME, 'wb') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=attributes)
    writer.writeheader()
    
    for user in users:
        row = {}
        for attribute in attributes:
            row[attribute] = user['attributes'][attribute]
        writer.writerow(row)

#=== End Main Script ===
