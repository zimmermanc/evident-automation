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
# API helper
#

from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime

import hashlib
import codecs
import hmac
import base64
import requests
import os

class ApiHelper():

    def __init__(self):
        """ Environment variables """

        # API keys from shell env
        self.pub_key = os.environ["ESP_ACCESS_KEY_ID"]
        self.secret_key = os.environ["ESP_SECRET_ACCESS_KEY"]


    def api_call(self, method, uri, data, timeout):
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
        secret = bytes(self.secret_key, 'UTF-8')
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
                    'Authorization' : 'APIAuth %s:%s' % (self.pub_key, auth) }

        # Using requests
        # http://docs.python-requests.org/en/latest/user/advanced/

        r = requests.Request(method, url+uri, data=data, headers=headers)
        p = r.prepare()
        s = requests.Session()
        ask = s.send(p, timeout=timeout)
        response = ask.json()

        return response

