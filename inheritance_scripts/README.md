### Copying configuration settings from one account to others

#### Requirements

1. Copy this folder of inheritance scripts
2. Install the ESP Python SDK: https://github.com/EvidentSecurity/esp-sdk-python2 
3. Install the 'tenacity' package by running `pip install tenacity`
4. Enter the 'template' account's name in the 'template\_account \_name' field of copy_account_configuration.py's options section
5. Enter the account names separated by commas into the 'target\_account\_names' field 
6. Enter 'True' for each type of setting you would like to copy from the template account to the target accounts
7. run `python3 copy_account_configuration.py`


#### The `options` fields example can be found below:


```
options = {
'template_account_name': 'Production account A', 
	'target_account_names': ['development account', 'development account X', 'operations account 3'],
	# Choose which configurations to inherit
	'inherit_disabled_signatures': True,
	'inherit_risk_levels': True,
	'inherit_scan_intervals': True,
	'inherit_integrations': False,
	'inherit_custom_signatures': True
	}
```