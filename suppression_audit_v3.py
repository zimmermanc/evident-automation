#!/usr/bin/env python
#
# Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
# 
#   Evident.io shall retain all ownership of all right, title and interest in and to 
#   the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
#   including (a) all information and technology capable of general application to Evident.io's
#   customers; and (b) any works created by Evident.io prior to its commencement of any
#   Services for Customer.
# 
# Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
#   Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
#   use, copy, configure and translate any Deliverable solely for internal business operations
#   of the Customer as they relate to the Evident.io platform and products, and always
#   subject to Evident.io's underlying intellectual property rights.
# 
# IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
#   INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
#   THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
#   THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
#   EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
#   OR MODIFICATIONS.
# 
# ---
#
# Provide customers with a csv file to audit suppressions configured in an ESP organization.
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

from api_helper import ApiHelper
from datetime import datetime

import json
import csv
import os
import re


def list_suppressions():
    """ List of up to 100 suppressions """

    api = ApiHelper()

    method = 'GET'
    uri = '/api/v2/suppressions?page[size]=100&include=regions,external_accounts,signatures,created_by'
    data = ''
    timeout = (3, 10)

    suppressions = api.api_call(method, uri, data, timeout)
    
    return suppressions


def element_search(suppressions, element_id):
    """ Search helper """

    return [ element for element in suppressions['included'] if element['id'] == element_id ]


def create_suppression_report(suppressions):
    """ Build a suppressions report """

    report = []
    for i, sup in enumerate(suppressions['data']):
        #print(i)

        # User email
        user_id = sup['relationships']['created_by']['data']['id']
        include = element_search(suppressions, user_id)
        try:
            email = include[0]['attributes']['email']
        except KeyError:
            email = ''

        # Signature name
        try:
            sig_id = sup['relationships']['signatures']['data'][0]['id']
        except IndexError:
            pass
        else:
            include = element_search(suppressions, sig_id)

        sig_name = ''
        for n in range(2):
            try:
                sig_name = include[n]['attributes']['name']
            except:
                pass

        # External account list
        ext_accounts = []
        for i in sup['relationships']['external_accounts']['data']:
            include = element_search(suppressions, i['id'])
            name = include[0]['attributes']['name']
            ext_accounts.append(name)
        esp_ext_accounts =  ", ".join( str(e) for e in ext_accounts)

        # Region list
        regions = []
        for i in sup['relationships']['regions']['data']:
            include = element_search(suppressions, i['id'])
            code = include[0]['attributes']['code']
            regions.append(re.sub('_', '-', code))
        aws_regions =  ", ".join( str(e) for e in regions)

        # Convert the date
        creation_date = datetime.strptime(sup['attributes']['created_at'], '%Y-%m-%dT%H:%M:%S.000Z')

        report_info = {
          'Suppression Type'  : sup['attributes']['suppression_type'],
          'Status'            : sup['attributes']['status'],
          'Reason'            : sup['attributes']['reason'],
          'Created On'        : creation_date.strftime("%B %d, %Y"),
          'Created By'        : email,
          'Signature'         : sig_name,
          'Resource'          : sup['attributes']['resource'],
          'External Accounts' : esp_ext_accounts,
          'Regions'           : aws_regions
        }

        report.append(report_info)

    return report


def create_csv_file(csv_file_name, report):
    """ Create csv formatted file """

    try:
        with open(csv_file_name, 'w') as f:
            head = [ 'Suppression Type', 'Status', 'Reason', 'Created On', 'Created By', 'Signature', 'Resource', 'External Accounts', 'Regions' ]
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
    """ Run checks and do the work """

    if os.path.exists(csv_file_name) == True:
        print('Error: The file ' + csv_file_name + ' already exists.')
        exit(1)

    suppressions = list_suppressions()
    if 'errors' in suppressions:
        print(json.dumps(suppressions, indent = 4))
        exit(1)

    report = create_suppression_report(suppressions)
    result = create_csv_file(csv_file_name, report)

    print(result)
        

if __name__ == "__main__":

  main(csv_file_name = 'esp_suppressions_report.csv')
