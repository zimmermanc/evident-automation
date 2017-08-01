#!/usr/bin/env python
#
# -------------------------------------------------------------------------------------------
# Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
# Evident.io shall retain all ownership of all right, title and interest in and to 
# the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
# including (a) all information and technology capable of general application to Evident.io's
# customers; and (b) any works created by Evident.io prior to its commencement of any
# Services for Customer.
#
# Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
# Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
# use, copy, configure and translate any Deliverable solely for internal business operations
# of the Customer as they relate to the Evident.io platform and products, and always
# subject to Evident.io's underlying intellectual property rights.
#
# IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
# INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
# THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
# THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
# EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
# OR MODIFICATIONS.
# -------------------------------------------------------------------------------------------
#
# Description:
#
# Requirements:
#
# * Python3 (Tested with version 3.6.1)
#   `python --version`
#
# * Valid ESP credentials / API keys
#   https://esp.evident.io/settings/api_keys
#   export ESP_ACCESS_KEY_ID=<your_access_key>
#   export ESP_SECRET_ACCESS_KEY=<your_secret_access_key>
#
# Options:
#
no_of_pages = 5     # search 250 log enteries
no_of_days  = 1     # return the last 24 hrs of activity
# --
#no_of_pages = 10    # search 500 log enteries
#no_of_days  = 3     # return the last 3 days of activity


from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

import hashlib
import codecs
import hmac
import base64
import requests
import os
import csv


# API keys from shell env
#
pub_key = os.environ["ESP_ACCESS_KEY_ID"]
secret_key = os.environ["ESP_SECRET_ACCESS_KEY"]
# or...
#pub_key = <your_esp_access_key_id>
#secret_key = <your_esp_secret_access_key>


def api_call(method, uri, data, timeout):
    """ API call """

    # ESP API endpoint - http://api-docs.evident.io/
    url = 'https://api.evident.io'

    # Uses the RFC-1123 spec. Note: Must be in the GMT timezone.
    now   = datetime.now()
    stamp = mktime(now.timetuple())
    dated = format_date_time(stamp)

    # The Content-MD5 header should include a MD5 base64 hexdigest of the request body.
    hex  = hashlib.md5(data.encode('UTF-8')).hexdigest()
    body = codecs.encode(codecs.decode(hex, 'hex'), 'base64').decode().rstrip('\n')

    # Create a canonical string using your HTTP headers containing the HTTP method,
    # content-type, content-MD5, request URI and the timestamp.
    canonical = '%s,%s,%s,%s,%s' % (method, 'application/vnd.api+json', body, uri, dated)

    # Convert from string to bytes.
    secret = bytes(secret_key, 'UTF-8')
    canonical = bytes(canonical, 'UTF-8')

    # Use the HMAC-SHA1 algorithm to encode the string with your secret key.
    hashed = hmac.new(secret, canonical, hashlib.sha1)
    encoded = base64.b64encode(hashed.digest())
    auth = str(encoded, 'UTF-8')

    # Add an Authorization header with the ‘APIAuth’, the public key, and the encoded
    # canonical string.

    headers = { 'Date'          : '%s' % (dated),
                'Content-MD5'   : '%s' % (body),
                'Content-Type'  : 'application/vnd.api+json',
                'Accept'        : 'application/vnd.api+json',
                'Authorization' : 'APIAuth %s:%s' % (pub_key, auth) }

    # Using requests
    # http://docs.python-requests.org/en/latest/user/advanced/

    r = requests.Request(method, url+uri, data=data, headers=headers)
    p = r.prepare()
    s = requests.Session()
    ask = s.send(p, timeout=timeout)
    response = ask.json()

    return response


def create_audit_report(today):
    """ Build an audit logs report """

    method = 'GET'
    data = ''
    timeout = (3, 10)

    report = []
    for n in range(no_of_pages):
        uri = '/api/v2/audit_logs.json?include=organization&page[number]=%d&page[size]=50' % (n + 1)
        response = api_call(method, uri, data, timeout)

        try:
            org_id   = response['included'][0]['id']
            org_name = response['included'][0]['attributes']['name']
        except KeyError:
            org_id = 'not found'; org_name = 'not found'

        try:
            output = response['data']
        except KeyError:
            pass
        else:
            for log in output:
                created_at = datetime.strptime(log['attributes']['created_at'], '%Y-%m-%dT%H:%M:%S.000Z')
                delta = today - created_at
                if delta.days >= no_of_days:
                    continue

                report_info = {
                  'id'                 : log['id'],
                  'platform'           : log['attributes']['platform'],
                  'created_at'         : log['attributes']['created_at'],
                  'organization_id'    : org_id,
                  'organization_name'  : org_name,
                  'user_email'         : log['attributes']['user_email'],
                  'user_ip'            : log['attributes']['user_ip'],
                  'access_denied'      : log['attributes']['access_denied'],
                  'successful'         : log['attributes']['successful'],
                  'action'             : log['attributes']['action'],
                  'item_type'          : log['attributes']['item_type'],
                  'item_id'            : log['attributes']['item_id']
                }

                report.append(report_info)

    return report


def create_csv_file(csv_file_name, report):
    """ Create csv formatted file """

    if report:
        try:
            with open(csv_file_name, 'w') as f:
                head = [ 'id', 'platform', 'created_at', 'organization_id', 'organization_name', 'user_email', 'user_ip', 'access_denied', 'successful', 'action', 'item_type', 'item_id' ]
                writer = csv.DictWriter(f, fieldnames=head)
                writer.writeheader()
                for row in report:
                    writer.writerow(row)
        except:
            pass

    if os.path.exists(csv_file_name) == True and os.stat(csv_file_name).st_size > 0:
        result = 'Success: Created ESP csv suppressions report, ' + csv_file_name +'.'
    else:
        result = 'Error: Failed to create csv file, ' + csv_file_name +'.'

    return result


def main(csv_file_name):
    """ Do the work... """

    today  = datetime.now()
    csv_file_name = csv_file_name + '_' + today.strftime("%Y%m%dT%H%M%S") + '.csv'
    
    report = create_audit_report(today)
    result = create_csv_file(csv_file_name, report)

    print(result)


if __name__ == "__main__":

    main(csv_file_name = 'esp_audit_report')
