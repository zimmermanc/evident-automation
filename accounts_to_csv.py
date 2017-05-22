import esp
import csv

# To run this script, please first:
# - Install the Python SDK: 'pip install esp'
# - Set ESP SDK Credentials as environment variables: 
#   https://esp.evident.io/settings/api_keys
#    1) run 'export ESP_ACCESS_KEY_ID=$access_key_from_above_link'
#    2) run 'export ESP_SECRET_ACCESS_KEY=$secret_access_key_from_above_link'
# - Run 'python3 accounts_to_csv.py' and the csv file will be saved 
#    in the same directory
def get_all_accounts():
    p_accounts = esp.ExternalAccount._all()
    accounts = []
    last_page = False
    while last_page == False:
        for acct in p_accounts:
            accounts.append(acct)
        try:
            p_accounts = p_accounts.next_page()
        except:
            last_page = True
    return accounts

def format_accounts_for_csv(accounts):
    f_accounts = []
    for acct in accounts:
        f_acct = {
            'name': acct.name,
            'account': acct.account,
            'sub-organization': acct.sub_organization.name,
            'team': acct.team.name,
            'updated_at': acct.updated_at
                }
        f_accounts.append(f_acct)
    return f_accounts

def generate_csv_from_accounts(accounts):
   with open('esp_accounts.csv', 'w') as file:
       headers = ['name', 'account', 'sub-organization', 'team', 'updated_at']
       writer = csv.DictWriter(file, fieldnames=headers)
       writer.writeheader()
       for acct in accounts:
           writer.writerow(acct)

def run():
    print("Starting...")
    accounts = get_all_accounts()
    accounts = format_accounts_for_csv(accounts)
    generate_csv_from_accounts(accounts)
    print("Finished")
    exit()

run()
