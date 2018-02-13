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
##
## This sript will output a CSV that includes risk levels for both built-in
## and custom signatures for all external accounts. 
## Requirements: 
##
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

options = {
	# Options:
	# ----- Using  'custom_risk_levels_only' will get built-in
	# signatures with a custom risk level as well as the
	# custom signatures for all accounts 
	# ----- Using 'all' will retrieve all built-in signatures
	# including those that use default risk levels as well as
	# the custom signatures for all accounts
	'signatures': 'custom_risk_levels_only'
}

def main(options):
	accounts_api = esp_sdk.ExternalAccountsApi()
	custom_signatures_api = esp_sdk.CustomSignaturesApi()
	# Get all accounts
	accounts = accounts_api.list()
	# Get signatures and their custom risk levels
	# for each account
	all_signatures = []
	resp = custom_signatures_api.list(include='external_accounts')
	for acct in accounts:
		# Retrieve the built-in signatures
		built_in_signatures = get_built_in_signatures_for_account(options, acct)
		for signature in built_in_signatures:
			all_signatures.append(signature)
		# Retrieve the custom signatures
		custom_signatures = get_custom_signatures_for_account(acct, resp)
		for signature in custom_signatures:
			all_signatures.append(signature)
	signatures_to_csv(all_signatures)
	exit()

def signatures_to_csv(signatures):
	with open('risk_levels_audit.csv', 'w', newline='') as file:
		writer = csv.writer(file)
		# Write headers
		writer.writerow([
				'ACCOUNT NAME', 
				'ACCOUNT ID',
				'SIGNATURE NAME',
				'SIGNATURE IDENTIFIER',
				'SIGNATURE_RISK_LEVEL',
				'CUSTOM_SIGNATURE'
			])

		for sig in signatures:
			writer.writerow([
				sig['account_name'], 
				sig['account_id'], 
				sig['signature_name'], 
				sig['signature_identifier'],
				sig['signature_risk_level'],
				sig['custom_signature']
			])
	return 

def get_built_in_signatures_for_account(options, account):
	signatures_api = esp_sdk.SignaturesApi()

	signatures = []

	if options['signatures'] == 'all':
	    filter = {}
	elif options['signatures'] == 'custom_risk_levels_only':
		filter = {'custom_risk_level_present': '1'}

	resp = signatures_api.list_with_custom_risk_level_for_external_account(
			account.id, 
			filter = filter
		)

	for sig in resp:
		if sig.custom_risk_level is not None:
			signatures.append({
				'account_name': account.name,
				'account_id': account.id,
				'signature_name': sig.name,
				'signature_identifier': sig.identifier,
				'signature_risk_level': sig.custom_risk_level,
				'custom_signature': False
			})
		else: 
			signatures.append({
				'account_name': account.name,
				'account_id': account.id,
				'signature_name': sig.name,
				'signature_identifier': sig.identifier,
				'signature_risk_level': sig.risk_level,
				'custom_signature': False
			})

	return signatures

def get_custom_signatures_for_account(account, custom_signatures):
	signatures = []

	for sig in custom_signatures:
		if account.id in sig.external_account_ids:
			signatures.append({
				'account_name': account.name,
				'account_id': account.id,
				'signature_name': sig.name,
				'signature_identifier': sig.identifier,
				'signature_risk_level': sig.risk_level,
				'custom_signature': True
			})
	
	return signatures

if __name__ == "__main__":
	main(options)