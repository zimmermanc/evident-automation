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
	integrations_api = esp_sdk.IntegrationsApi()
	template_integrations = get_integrations_for_account(
		accounts['template_account_id'],
		integrations_api
		)
	copy_config_to_accounts(accounts['target_account_ids'], template_integrations, integrations_api)
	return

def copy_config_to_accounts(target_account_ids, template_integrations, integrations_api):
	target_account_ids = set(target_account_ids)

	for integration in template_integrations:
		existing_account_ids = set(integration.external_account_ids)

		if target_account_ids.issubset(existing_account_ids) == False:
			account_ids = existing_account_ids.union(target_account_ids)			
			account_ids = list(account_ids)
			add_accounts_to_integration(integration.id, account_ids, integrations_api)
	return

@retry(wait=wait_exponential(multiplier=1, max=10))
def get_integrations_for_account(account_id, integrations_api):
	all_integrations = integrations_api.list(
		include='external_accounts'
		)
	integrations = []

	for integration in all_integrations:
		if account_id in integration.external_account_ids:
			integrations.append(integration)
	
	return integrations

@retry(wait=wait_exponential(multiplier=1, max=10))
def add_accounts_to_integration(integration_id, account_ids, integrations_api):
	sns_api = esp_sdk.IntegrationsAmazonSNSApi()
	resp = sns_api.update(
				integration_id,
				external_account_ids = account_ids
				)
	# Activate integration
	integrations_api.test_notify(integration_id)
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