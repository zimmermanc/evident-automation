## Azure Onboarding Scripts

### Table of Contents

#### Scenarios

* Onboarding master or standalone subscription (no existing activity log export)
* Onboarding master or standalone subscription (existing activity log export)
* Onboarding slave subscription

#### Onboarding Steps

1. Unzip Onboard_azure.zip
2. Install the required python libraries
3. Login to Azure cli
4. Create a temporary Service Principal
5. Grant ESPtemponboarding App permissions to Azure AD
6. Get ESP team ID and credential
7. Edit onboard_azure_account.py options
8. Run the onboarding script

---

## Scenarios

#### Terminology

* **Master**: The first subscription that you want to onboard to ESP. Typically, you set this subscription as a designated location for Activity log export for the rest of your subscriptions
* **Slave/additional subscription**: This subscription typically exports its activity log to the master subscription.

### Onboarding master or standalone subscription (no existing activity log export)

In this scenario, you have one Azure subscription that you want to onboard, either as master or standalone ESP account. The onboarding script will create a log profile and a storage account to store your activity log.

#### Follow step 1-8 shown in the Onboarding Steps section. Sample config:
```
options = {
	'esp_team_id': '1234',
	'tenant_id': '00000000-0000-0000-0000-000000000',
	'script_service_principal_client_id': '11111111-1111-1111-1111-111111111111',
	'script_service_principal_secret': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',

	'subscriptions_to_onboard': ['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'],
	'subscriptions_to_exclude': [],
	'logs_retention_time': '7',

	'subscription_id_for_unified_logs': False,
	'existing_logs_storage_account_id': False,
	'existing_logs_storage_account_name': False,

	'esp_group_id': False,
	'Existing_logs_storage_account_key': False,

	'remove_existing_log_profile': True,
	'template': arm_template,
	'dry_run': True
}
```

If the script finish without error, you should see **onboarding_results<timestamp>.csv** generated in the same directory. If you are onboarding the subscription as master, you should keep this file as it contains information needed to onboard slaves/additional subscriptions.

### Onboarding master or standalone subscription (existing activity log export)

In this scenario, you have one Azure subscription that you want to onboard, either as master or standalone ESP account. You also have an existing Activity log export to your own storage account, and you want ESP to leverage your existing storage account.

#### Follow step 1-8 shown in the Onboarding Steps section. Sample config:
```
options = {
	'esp_team_id': '1234',
	'tenant_id': '00000000-0000-0000-0000-000000000',
	'script_service_principal_client_id': '11111111-1111-1111-1111-111111111111',
	'script_service_principal_secret': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',

	'subscriptions_to_onboard': ['aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'],
	'subscriptions_to_exclude': [],
	'logs_retention_time': '7',

	'subscription_id_for_unified_logs': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
	'existing_logs_storage_account_id': '/subscriptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/resourceGroups/suba-rgroup/providers/Microsoft.Storage/storageAccounts/myCurrentStorageLog',
	'existing_logs_storage_account_name': 'myCurrentStorageLog',

	'esp_group_id': False,
	'existing_logs_storage_account_key': 'xxxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxxxxxxx+xxx/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx==',

	'remove_existing_log_profile': True,
	'template': arm_template,
	'dry_run': True
}
```

If the script finish without error, you should see **onboarding_results<timestamp>.csv** generated in the same directory. If you are onboarding the subscription as master, you should keep this file as it contains information needed to onboard slaves/additional subscriptions.

### Onboarding slave subscription

In this scenario, you have onboarded your master subscription, and you want to onboard additional subscriptions to ESP. If you still have the details of the **ESPtemponboarding** service principal from step 4, you should already have the following information:
* esp_team_id
* tenant_id
* script_service_principal_client_id
* script_service_principal_secret

You should be able to get the following information in the onboarding_results<timestamp>.csv which is generated when you have successfully onboarded your master subscription:
* subscription_id_for_unified_logs (Subscription)
* existing_logs_storage_account_id (Storage Account ID)
* existing_logs_storage_account_name (Storage Account Name)
* esp_group_id (ESP Azure Group ID)

#### Follow step 3 (Login to Azure CLI), then step 6-8. Sample config:
```
options = {
	'esp_team_id': '1234',
	'tenant_id': '00000000-0000-0000-0000-000000000',
	'script_service_principal_client_id': '11111111-1111-1111-1111-111111111111',
	'script_service_principal_secret': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',

	'subscriptions_to_onboard': ['bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb','cccccccc-cccc-cccc-cccc-cccccccccccc'],
	'subscriptions_to_exclude': [],
	'logs_retention_time': '7',

	'subscription_id_for_unified_logs': 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
	'existing_logs_storage_account_id': '/subscriptions/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/resourceGroups/suba-rgroup/providers/Microsoft.Storage/storageAccounts/myCurrentStorageLog',
	'existing_logs_storage_account_name': 'myCurrentStorageLog',
	'esp_group_id': '45',  

	'existing_logs_storage_account_key': False,

	'remove_existing_log_profile': True,
	'template': arm_template,
	'dry_run': True
}
```

---

## Onboarding Steps

### Step 1: Download the script and resources directory

Please download the directory located in the Evident automation repository here:
[onboard_azure_subscriptions](https://github.com/EvidentSecurity/automation/tree/master/onboard_azure_subscriptions)

Inside the folder you should see esp-trigger.zip , onboard_azure_account.py, requirements.txt


### Step 2: Install the required python libraries

```
pip install -r requirements.txt
```


### Step 3: Login to Azure cli

Install Azure CLI (if not yet installed)
[Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)

Login to Azure CLI
```
az login
```


### Step 4: Create a temporary Service Principal

This step is only valid if you are onboarding **master** or **standalone** subscription to ESP. *Skip this step is you are onboarding additional subscriptions/ESP accounts and still have **ESPtemponboarding** SP from the previous onboarding.*


Run the following command to create a temporary Service Principal. Contributor permission is required in order to publish the function app.
```
az ad sp create-for-rbac -n "ESPtemponboarding" --role contributor --scopes /subscriptions/00000000-0000-0000-0000-000000000000
```

**Please save the service principal details. You can re-use this temporary SP to onboard additional subscriptions.**


### Step 5: Grant ESPtemponboarding App permissions to Azure AD

The onboarding script is going to create a permanent ESP Service principal. In order to do so, **ESPtemponboarding** needs to be given access to create/write App.

1. Go to **Azure Active Directory** => **App Registrations** => **ESPtemponboarding** => **Required permissions**
2. Select **+Add** button => **Select API**
3. Select **Windows Azure Active Directory**
4. Click on **Select** Button
5. Check the following permissions:
- [x] Read directory data
- [x] Read and write all applications
- [x] Read all users' full profile
6. Click on **Select** button, then click on **Done** button
7. Select **Microsoft Graph**
8. Click on **Select** Button
9. Check the following permissions:
- [x] Read all users' full profiles
10. Click on **Select** button, then click on **Done** button
11. Once you have added both AAD and Graph permission, select **Grant Permission** and hit **Yes**


### Step 6: Get ESP team ID and credential

#### TEAM ID
You can go to https://esp.evident.io/control_panel/teams and select edit. The team ID is included in the url

#### API KEY
```
export ESP_ACCESS_KEY_ID='your_esp_access_key_id'
export ESP_SECRET_ACCESS_KEY='your_esp_secret_access_key'
```

Or add the credential to onboard_azure_account.py directly:
```
esp_public_key = os.environ["ESP_ACCESS_KEY_ID"]
esp_secret_key = os.environ["ESP_SECRET_ACCESS_KEY"]
```


### Step 7: Edit onboard_azure_account.py options

See **Scenarios** section for sample config


### Step 8: Run the onboarding script

By default, the script runs in dry-run state. We recommend that you run the dry mode first before running the actual onboarding.

```
python onboard_azure_account.py
```


To run the onboarding, disable dry-run mode:
```
python onboard_azure_account.py --dry-run False
```


**NOTE**: If your subscription does not have Microsoft.Insights subscriptions, the script will enable Insights subscriptions, and it may take up to 1 hour to complete the subscription.

