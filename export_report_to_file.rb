# Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
#   Evident.io shall retain all ownership of all right, title and interest in and to 
#   the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
#   including (a) all information and technology capable of general application to Evident.io's customers; 
#   and (b) any works created by Evident.io prior to its commencement of any Services for Customer. 
#
# Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
#   Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
#   use, copy, configure and translate any Deliverable solely for internal business operations of the Customer 
#   as they relate to the Evident.io platform and products, 
#   and always subject to Evident.io's underlying intellectual property rights.
#
# IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
#   INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
#   THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, 
#   EVEN IF EVIDENT.IO HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#  THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
#  THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
#  EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
# -------------------------------------------------------------------------------------------
# Description:
#
# This script dumps a list of ESP users for an organization to a csv file called,
# "esp_users_report.csv" in the same directory that the script is executed in.
# Alternatively, you can simply list ESP users in json format to the screen.
#
# Requirements:
#
# * Ruby and the following Ruby gems:
# rest-client, api-auth, digest, json
#
# * Valid ESP API keys
#   https://esp.evident.io/settings/api_keys
#  
# * Please go to 'User Config Options below'
#
require 'rest-client'
require 'api-auth'
require 'digest'
require 'json'

# User Config options
access_key_id = ''        # ESP ACCESS KEY GOES HERE as string
secret_access_key = ''    # ESP SECRET ACCESS KEY GOES HERE as string
file_format_type = 'CSV'  # Can be CSV, PDF, or JSON
report_ids = []           # Enter report_ids requested in an array, e.g. [1,2,3]

body = {'data': {
          'attributes': {
            'requested_format': file_format_type,
            'report_ids': report_ids
            }
          }
        }

json_body = JSON.dump(body)
encoded_body = Digest::MD5.base64digest(json_body)
headers = { 
        'Accept' => "application/vnd.api+json",
        'Content-MD5' => encoded_body,
        'Content-Type' => "application/vnd.api+json",
        'Date' => Time.now.httpdate,
        }

@request = RestClient::Request.new(
        :url => "https://api.evident.io/api/v2/reports/export/files",
        :headers => headers,
        :method => :post, 
        :payload => json_body
        )

@signed_request = ApiAuth.sign!(@request, access_key_id, secret_access_key)
@signed_request.execute do |response, request, result|
  puts response.body
end