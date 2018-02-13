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
	'signatures': 'all'
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
	with open('signatures.csv', 'w', newline='') as file:
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