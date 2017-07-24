#!/usr/bin/env python
#
# PROVIDED AS IS WITH NO WARRANTY OR GUARANTEES
# Copyright (c) 2017 Evident.io, Inc., All Rights Reserved
#

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

    ##hex  = hashlib.md5(data.encode('UTF-8'))
    ##b64  = base64.b64encode(hex.digest())
    ##body = str(b64, 'UTF-8')

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

    if response['data']:
        ext_accts = []
        for item in response['data']: 
            #print('Id: %s\tName: %s' % (item['id'], item['attributes']['name']))
            ext_accts.append(item['id'])

    return ext_accts


def list_disabled_signatures(ext_accts):
    """ List disabled signatures """

    method = 'GET'
    ##uri = '/api/v2/external_accounts/<external_account_id>/disabled_signatures'
    data = ''
    timeout = (3, 10)

    for acct in ext_accts:
        uri = '/api/v2/external_accounts/%s/disabled_signatures' % (acct)
        response = api_call(method, uri, data, timeout)
        if response['data']:
            print('Account ID: %s' % (acct))
            print(json.dumps(response, indent = 4))


def disable_signature(ext_accts, sig_id=141):
    """ Disable a signature """

    method = 'POST'
    ##uri = '/api/v2/external_accounts/<external_account_id>/disabled_signatures'
    data = '{"data": {"type": "disabled_signatures", "attributes": {"signature_id": %d}}}' % (sig_id)
    timeout = (3, 10)

    for acct in ext_accts:
        uri = '/api/v2/external_accounts/%s/disabled_signatures' % (acct)
        response = api_call(method, uri, data, timeout)
        print(response)

    return


def main():

    ext_accts = list_external_accounts()
    disable_signature(ext_accts)
    #list_disabled_signatures(ext_accts)


if __name__ == "__main__":

    main()
