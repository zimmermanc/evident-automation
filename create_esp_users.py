#!/usr/bin/env python
#
# PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
# Copyright (c) 2017 Evident.io, Inc., All Rights Reserved
#
# This script reads from a csv file containing a list of ESP users and attempts to create each one.
# It looks for a file called "esp_users.csv" is the same directory the script is executed in.
#
# CSV File Format:
# First Name,Last Name,Email,Role
# Jimmy,Page,jimmy@rock.io,customer
# Randy,Rhodes,randy@rock.io,manager
# Eric,Clapton,eric@rock.io,manager
#
# The first 3 fields are required; First Name, Last Name and Email. If the role field is left blank,
# i.e. 'Eric,Clapton,eric@rock.io,' the default role is "manager."
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
# Options:
#
csv_delimiter = ','
fields = 4

import esp_sdk
import csv
import os
import re

def read_user_data(csv_file_name):
    """ Read ESP users csv file """

    users = []
    with open(csv_file_name) as csvUserData:
        csvReader = csv.reader(csvUserData, delimiter = csv_delimiter)
        for row in csvReader:
            if len(row) != fields:
                continue
            if re.search('[@]', row[2]) == None:
                continue

            skip = 'false'
            for i in range(2):
                if re.match('[A-Za-z]', row[i]) == None:
                    skip = 'true'; break 

            if skip != 'true':
                user = ( row[0], row[1], row[2], row[3] )
                users.append(user)

    return users


def create_esp_users(users_api, users):
    """ Create ESP users """

    for user in users:
        role_id = '3' if (user[3] == 'customer') else '2'
        esp_user = users_api.create(user[0], user[1], user[2], role_id=role_id)
        print('Created ESP user -> %s' % (esp_user.email))

    return


def main(csv_file_name):
    """ Run checks and do the work """

    try:
        users_api = esp_sdk.UsersApi()
        test_api  = users_api.list()
    except esp_sdk.rest.ApiException as e:
        if str(e.status) == '401':
            print('Error: Please check your ESP credentials / API keys.')
        else:
            print(e)
        exit(1)

    if os.path.exists(csv_file_name) != True:
        print("Error: Can't find file, " + csv_file_name + '.')
        exit(1)

    users  = read_user_data(csv_file_name)
    result = create_esp_users(users_api, users)


if __name__ == "__main__":

  main(csv_file_name = 'esp_users.csv')
