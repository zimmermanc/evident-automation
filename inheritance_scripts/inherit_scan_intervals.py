## Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
## 
##   Evident.io shall retain all ownership of all right, title and interest in and to 
##   the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
##   including (a) all information and technology capable of general application to Evident.io's
##   customers; and (b) any works created by Evident.io prior to its commencement of any
##   Services for Customer.
## 
## Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
##   Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
##   use, copy, configure and translate any Deliverable solely for internal business operations
##   of the Customer as they relate to the Evident.io platform and products, and always
##   subject to Evident.io's underlying intellectual property rights.
## 
## IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
##   INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
##   THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
##   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
## 
## EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
##   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
##   THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
##   EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
##   OR MODIFICATIONS.
## 
## ---
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
from tenacity import *

options = {
	'template_account_name': '', 
	'target_account_names': ['']
	}

def run(accounts):
	scan_intervals_api = esp_sdk.ScanIntervalsApi()
	template_scan_intervals = get_scan_intervals_for_account(accounts['template_account_id'], scan_intervals_api)
	copy_config_to_accounts(accounts['target_account_ids'], template_scan_intervals, scan_intervals_api)
	return

def copy_config_to_accounts(target_accounts, template_scan_intervals, scan_intervals_api):
	for account in target_accounts:
		existing_scan_intervals = get_scan_intervals_for_account(account, scan_intervals_api)
		for sc_int in existing_scan_intervals:
			remove_scan_interval(sc_int, scan_intervals_api)
		for sc_int in template_scan_intervals:
			create_scan_interval(account, sc_int, scan_intervals_api)
	
	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def get_scan_intervals_for_account(account_id, scan_intervals_api):
	scan_intervals = scan_intervals_api.list_for_external_account(
			account_id, 
			page = {'size': 100}
		)
	return scan_intervals

@retry(wait=wait_exponential(multiplier=1, max=10))
def create_scan_interval(account_id, scan_interval, scan_intervals_api):
	resp = scan_intervals_api.create(account_id, scan_interval.interval, scan_interval.service_id)
	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def remove_scan_interval(scan_interval, scan_intervals_api):
	resp = scan_intervals_api.delete(scan_interval.id)
	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def get_accounts(options, accounts_api):
	accounts = {
		'template_account_id': None,
		'target_account_ids': []
	}
	# Compare account names in lower case so that options
	# don't have to be case-sensitive
	options['template_account_name'] = options['template_account_name'].lower()
	options['target_account_names'] = [name.lower() for name in options['target_account_names']]
	# Get all accounts and filter locally to 
	# reduce to prevent API request throttling
	all_accounts = accounts_api.list(page={'size': 100})
	for acct in all_accounts:
		acct_name = acct.name.lower()
		if acct_name == options['template_account_name']:
			accounts['template_account_id'] = acct.id
		if acct_name in options['target_account_names']:
			accounts['target_account_ids'].append(acct.id)

	return accounts

def main(options):
	accounts_api = esp_sdk.ExternalAccountsApi()
	# Get Account Info
	accounts = get_accounts(options, accounts_api)
	run(accounts)
	exit()

if __name__ == "__main__":
	main(options)