#!/usr/bin/env python
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
