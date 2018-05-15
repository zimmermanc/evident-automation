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
import time

def main():
	# Initialize required API endpoints 
	accounts_api = esp_sdk.ExternalAccountsApi()
	reports_api = esp_sdk.ReportsApi()
	report_export_api = esp_sdk.ReportExportApi()
	# Get a list of accounts
	all_accounts = accounts_api.list(page={'size': 100})
	account_ids = []
	for acct in all_accounts:
		account_ids.append(acct.id)
	# Get a list of recent reports
	all_reports = reports_api.list(page={'size': 100})
	reports = []
	for report in all_reports:
		if len(reports) >= len(account_ids):
			break
		reports.append({'report_id': report.id, 'account_id': report.external_account_id})

	# Ensure there are no more and no less than one report for each account
	report_ids = []
	for account_id in account_ids:
		count = 0
		for report in reports:
			if report['account_id'] == account_id and count < 1:
				count += 1 
				report_ids.append(report['report_id'])
			elif count >= 1:
				break
		if count == 0:
			time.sleep(2)
			report_to_add = reports_api.list(filter={'external_account_id_eq': account_id})[0]
			report_ids.append(report_to_add.id)

	# Request file export
	response = report_export_api.request_file(
			'csv',
			report_ids,
			include='exported_report'
	)

	print('The exported report has been requested and will be sent to your email')
	exit()

if __name__ == "__main__":
	main()