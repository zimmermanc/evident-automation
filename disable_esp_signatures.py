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
# Disables one or more ESP signatures by name in all external accounts. Signature names are
# supplied as arguments.
#
# Example: disable_esp_signatures.py -s 'Signature One' 'Signature Two' 'Signature Three' ...
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
# You can exclude one or more external accounts by including them in an exclude list:
acct_exclude_list = [ '1111', '2222' ]


from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

import hashlib
import codecs
import hmac
import base64
import requests
import json
import os
import re
import argparse

# API keys from shell env
pub_key = os.environ["ESP_ACCESS_KEY_ID"]
secret_key = os.environ["ESP_SECRET_ACCESS_KEY"]


def usage():
    print('usage:', sys.argv[0], '[-h] -s <\'signature names\'>')
    sys.exit(1)


def script_args():
    p = argparse.ArgumentParser(description='Signature names.')
    p.add_argument ('-s', nargs='+', metavar = '<\'signature one\' \'signature two\' >', type = str, help = 'one or more signature names in quotes', required = True)
    args = p.parse_args()

    return args


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


def list_external_accounts():
    """ List external accounts """

    method = 'GET'
    uri = '/api/v2/external_accounts'
    data = ''
    timeout = (3, 10)

    response = api_call(method, uri, data, timeout)

    ext_acct_ids = []
    try:
        for acct in response['data']: 
            acct_id = acct['id']
            if acct_id in acct_exclude_list:
                continue
            ext_acct_ids.append(acct_id)
    except KeyError:
        pass

    return ext_acct_ids


def list_signatures(sig_names):
    """ Convert Signature names to Ids """

    method = 'GET'
    data = ''
    timeout = (3, 10)

    sig_ids = []
    for sig_name in sig_names:
        sig_name = re.sub('\s', '+', sig_name)
        uri = '/api/v2/signatures.json?filter[name_eq]=%s' % (sig_name)
        response = api_call(method, uri, data, timeout)

        try:
            sig_id = response['data'][0]['id']
        except IndexError:
            pass
        else:
            sig_ids.append(int(sig_id))

    return sig_ids


def disable_signatures(ext_acct_ids, sig_names):
    """ Disable one or more signatures """

    method = 'POST'
    timeout = (3, 10)

    sig_ids = list_signatures(sig_names)

    for acct in ext_acct_ids:
        uri = '/api/v2/external_accounts/%s/disabled_signatures' % (acct)

        for sig_id in sig_ids:
            data = '{"data": {"type": "disabled_signatures", "attributes": {"signature_id": %d}}}' % (sig_id)
            response = api_call(method, uri, data, timeout)
            response['signature_id'] = sig_id
            response['account_id'] = acct
            print(json.dumps(response, indent=4, sort_keys=True))

    return


def main():
    """ Do the work... """

    args = script_args()
    if args.s == '':
        usage()

    ext_acct_ids = list_external_accounts()
    disable_signatures(ext_acct_ids, args.s)


if __name__ == "__main__":

    main()
