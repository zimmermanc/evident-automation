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
# This script dumps a list of ESP users for an organization to a csv file called,
# "esp_users_report.csv" in the same directory that the script is executed in.
# Alternatively, you can simply list ESP users in json format to the screen.
#
# Requirements:
#
# * Python3 (Tested with version 3.6.1)
#   `python --version`
#
# * Install the ESP Python SDK
#   https://github.com/EvidentSecurity/esp-sdk-python2 
# 
# * Valid ESP credentials / API keys
#   https://esp.evident.io/settings/api_keys
#   export ESP_ACCESS_KEY_ID=<your_access_key>
#   export ESP_SECRET_ACCESS_KEY=<your_secret_access_key>
#

import esp_sdk
import csv
import os
import json
import sys
import argparse

def usage():
    print('usage:', sys.argv[0], '[-h] -o <output>')
    sys.exit(1)

def script_args():
    p = argparse.ArgumentParser(description='Output option.')
    p.add_argument ('-o', metavar = '<output>', type = str, help = 'csv or json', required = True)
    args = p.parse_args()

    return args


def create_user_report(users):
    """ Build a user report """

    report = []
    for u, user in enumerate(users):

        report_info = {
          'First Name'       : user.first_name,
          'Last Name'        : user.last_name,
          'Email'            : user.email,
          'Role'             : user.role.name,
          'Organization'     : user.organization.name,
          'Last Updated'     : user.updated_at.strftime("%b %d, %Y %I:%M:%S %p"),
          'MFA Enabled'      : user.mfa_enabled
        }

        report.append(report_info)

    return report


def create_csv_file(csv_file_name, report):
    """ Create csv formatted file """

    try:
        with open(csv_file_name, 'w') as f:
            head = [ 'First Name', 'Last Name', 'Email', 'Role', 'Organization', 'Last Updated', 'MFA Enabled' ]
            writer = csv.DictWriter(f, fieldnames=head)
            writer.writeheader()
            for row in report:
                writer.writerow(row)
    except:
        pass 

    if os.path.exists(csv_file_name) == True and os.stat(csv_file_name).st_size > 0:
        result = 'Success: Created ESP csv user report, ' + csv_file_name +'.'
    else:
        result = 'Error: Failed to create csv file, ' + csv_file_name +'.'

    return result


def main(csv_file_name):
    """ Run checks and do the work """

    args = script_args()
    if args.o != 'json' and args.o != 'csv':
        usage()

    try:
        users_api = esp_sdk.UsersApi()
        users = users_api.list(include='role,organization,sub_organizations,teams')
    except esp_sdk.rest.ApiException as e:
        if str(e.status) == '401':
            print('Error: Please check your ESP credentials / API keys.')
        else:
            print(e)
        sys.exit(1)

    if args.o == 'json':
        report = create_user_report(users)
        print(json.dumps(report, sort_keys=False, indent=4))
    elif os.path.exists(csv_file_name) == True:
        print('Error: The file ' + csv_file_name + ' already exists.')
        sys.exit(1)
    else:
        report = create_user_report(users)
        result = create_csv_file(csv_file_name, report)
        print(result)
        

if __name__ == "__main__":

  main(csv_file_name = 'esp_users_report.csv')
