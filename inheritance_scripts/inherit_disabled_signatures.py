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
	accounts_api = esp_sdk.ExternalAccountsApi()
	disabled_signature_ids = get_disabled_signatures_for_account(accounts['template_account_id'], accounts_api)
	copy_config_to_accounts(accounts['target_account_ids'], disabled_signature_ids, accounts_api)
	return

def copy_config_to_accounts(target_account_ids, disabled_signature_ids, accounts_api):
	template_disabled_signature_ids = set(disabled_signature_ids)
	for account in target_account_ids:
		# Get the existing disabled signatures for target account
		existing_disabled_signature_ids = set(get_disabled_signatures_for_account(account, accounts_api))
		# Disable signatures that are not already disabled in the target account
		signatures_to_disable = template_disabled_signature_ids.difference(existing_disabled_signature_ids)
		for sig_id in signatures_to_disable:
			disable_signature(account, sig_id , accounts_api)
		# Re-enable any signatures that are disabled and not in the template disabled 
		# signatures list
		signatures_to_enable = existing_disabled_signature_ids.difference(template_disabled_signature_ids)
		for sig_id in signatures_to_enable:
			enable_signature(account, sig_id, accounts_api)

	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def get_disabled_signatures_for_account(account_id, accounts_api):
	signatures = accounts_api.list_disabled_signatures(
			account_id, 
			page = {'size': 100}
		)
	signature_ids = [sig.id for sig in signatures]
	return signature_ids

@retry(wait=wait_exponential(multiplier=1, max=10))
def disable_signature(account_id, signature_id, accounts_api):
	resp = accounts_api.add_disabled_signature(account_id, signature_id)
	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def enable_signature(account_id, signature_id, accounts_api):
	resp = accounts_api.remove_disabled_signature(account_id, signature_id)
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