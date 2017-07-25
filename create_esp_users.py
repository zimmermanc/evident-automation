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
# This script reads from a csv file containing a list of ESP users and attempts to create each one.
# It looks for a file called "esp_users.csv" is the same directory the script is executed in.
#
# CSV File Format:
#
# First_Name,Last_Name,Email,Role,Teams
# Jimmy,Page,jimmy@rock.io,customer,TeamA,TeamB
# Randy,Rhodes,randy@rock.io,manager,TeamB
# Eric,Clapton,eric@rock.io,manager
#
# The first 3 fields are required; First_Name, Last_Name and Email. The Role and Teams fields
# are optional. The default role is "manager" if one is not given.
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
csv_delimiter = ','
req_fields = 3


from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

import hashlib
import codecs
import hmac
import base64
import requests
import json
import csv
import os
import re

# API keys from shell env
pub_key = os.environ["ESP_ACCESS_KEY_ID"]
secret_key = os.environ["ESP_SECRET_ACCESS_KEY"]


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


def read_user_data(csv_file_name):
    """ Read ESP users csv file """

    users = []
    with open(csv_file_name, 'r') as csvUserData:
        csvReader = csv.reader(csvUserData, delimiter = csv_delimiter)
        for row in csvReader:
            if len(row) < req_fields:
                continue
            if re.match('[A-Za-z]', row[0]) == None or re.match('[A-Za-z]', row[1]) == None:
                continue
            if re.search('[@]', row[2]) == None:
                continue

            try:
                role = row[3]
            except IndexError:
                role = ''

            try:
                team_names = []
                for team in row[4:]:
                    team = re.sub('\s', '+', team)
                    team_names.append(team)
            except IndexError:
                team_names = ''

            team_ids = list_esp_teams(team_names)

            user = ( row[0], row[1], row[2], role, team_ids )
            users.append(user)

    return users


def list_esp_teams(team_names):
    """ Convert Team names to Ids """

    method = 'GET'
    ##uri = '/api/v2/teams'
    data = ''
    timeout = (3, 10)

    team_ids = []
    for team in team_names:
        uri = '/api/v2/teams.json?filter[name_eq]=%s' % (team)
        response = api_call(method, uri, data, timeout)
        
        try:
            team_id = response['data'][0]['id']
        except KeyError:
            pass
        else:
            team_ids.append(int(team_id))

    return team_ids


def create_esp_users(users):
    """ Create ESP users """

    method = 'POST'
    uri = '/api/v2/users'
    ##data = ''
    timeout = (3, 10)

    for user in users:
        role_id = '3' if (user[3] == 'customer') else '2'
        data = '{"data": {"type": "users", "attributes": {"first_name": "%s", "last_name": "%s", "email": "%s", "role_id": "%s", "team_ids": %s }}}' % (user[0], user[1], user[2], role_id, user[4] )
        response = api_call(method, uri, data, timeout)

        try:
            print('Created ESP user -> %s' % (response['data']['attributes']['email']))
        except KeyError:
            print('Failed to create ESP user -> %s' % (user[2]))

    return


def main(csv_file_name):
    """ Run checks and do the work """

    if os.path.exists(csv_file_name) != True:
        print("Error: Can't find file, " + csv_file_name + '.')
        exit(1)

    users  = read_user_data(csv_file_name)
    result = create_esp_users(users)


if __name__ == "__main__":

  main(csv_file_name = 'esp_users.csv')
