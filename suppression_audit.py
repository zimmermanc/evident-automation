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
# Provide customers with a csv file to audit suppressions configured in an ESP organization.
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
import re
import os

def create_suppression_report(suppressions):
    """ Build a suppressions report """

    report = []
    for s, sup in enumerate(suppressions):

        try:
            sig = sup.signatures[0].name
        except:
            sig = 'n/a'

        regions = []
        for r, region in enumerate(sup.regions):
            regions.append(re.sub('_', '-', region.code))
        aws_regions =  ", ".join( str(e) for e in regions)

        report_info = {
          'Suppression Type' : sup.suppression_type,
          'Status'           : sup.status,
          'Reason'           : sup.reason,
          'Created On'       : sup.created_at.strftime("%B %d, %Y"),
          'Created By'       : sup.created_by.email,
          'External Account' : sup.external_accounts[0].name,
          'Signature'        : sig,
          'Resource'         : sup.resource,
          'Regions'          : aws_regions
        }

        report.append(report_info)

    return report


def create_csv_file(csv_file_name, report):
    """ Create csv formatted file """

    try:
        with open(csv_file_name, 'w') as f:
            head = [ 'Suppression Type', 'Status', 'Reason', 'Created On', 'Created By', 'External Account', 'Signature', 'Resource', 'Regions' ]
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

    try:
        suppressions_api = esp_sdk.SuppressionsApi()
        suppressions = suppressions_api.list(include='regions,external_accounts,signatures,created_by')
    except esp_sdk.rest.ApiException as e:
        if str(e.status) == '401':
            print('Error: Please check your ESP credentials / API keys.')
        else:
            print(e)
        exit(1)

    if os.path.exists(csv_file_name) == True:
        print('Error: The file ' + csv_file_name + ' already exists.')
        exit(1)

    report = create_suppression_report(suppressions)
    result = create_csv_file(csv_file_name, report)

    print(result)
        

if __name__ == "__main__":

  main(csv_file_name = 'esp_suppressions_report.csv')
