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
# Description: 
# 	This script is an example of how to get alert stats and changes using the ESP Ruby SDK. For example, 
#   this script will grab the current high risk fail alert count and compare it with the high risk fail 
#   count from 5 days ago. 
#
# Requirements:
# 	Please install the ESP Ruby SDK found here: https://github.com/EvidentSecurity/esp-sdk-ruby
#
require 'esp_sdk'
require 'time'
require 'cgi'
require 'openssl'

config = ESP::Configuration.new

# ESP API Keys
config.access_key_id = ''
config.secret_access_key = ''

# Account_id
account_id = ''
# Date Range
before_date = '2017-12-05'
after_date = '2017-12-07'
# Alert properties
status = 'fail'
risk_level = 'high'

# Declare APIs
reports_api = ESP::ReportsApi.new
alerts_api = ESP::AlertsApi.new

def get_alert_count_for_report_total(alerts)
  total_pages = alerts.last_page_number
  if total_pages == nil
  	total_pages = 1
  end
  alerts.last_page!
  total = ((total_pages.to_i - 1) * 20) + alerts.size.to_i
  return total
end

# Get after report and high risk alert count
opts = {}
opts[:filter] =  { 
  external_account_id_eq: account_id.to_s,
  created_at_lt: after_date
}
opts[:filter] = {}
current_report = reports_api.list(opts)[0]
opts[:filter] = {
  status_eq: status,
  risk_level_eq: risk_level
}
current_alerts = alerts_api.list_for_report(current_report.id, opts)
current_alert_count = get_alert_count_for_report_total(current_alerts)

# Get before report and high risk alert count 
opts[:filter] = {}
opts[:filter] =  { 
  external_account_id_eq: account_id.to_s,
  created_at_lt: before_date
}
opts[:filter] = {}
prior_report = reports_api.list(opts)[0]
opts[:filter] = {
  status_eq: status,
  risk_level_eq: risk_level
}
prior_alerts = alerts_api.list_for_report(prior_report.id, opts)
prior_alert_count = get_alert_count_for_report_total(prior_alerts)

# Calculate difference
alert_count_change = current_alert_count - prior_alert_count
puts 'Before alert count:'
puts prior_alert_count
puts 'After alert count:'
puts current_alert_count
puts 'Difference:'
puts alert_count_change