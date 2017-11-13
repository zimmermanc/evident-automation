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
import argparse
import uuid
import hashlib
import codecs
import hmac
import base64
import requests
import os
import json
import io
import csv
import xmltodict
from datetime import datetime, timezone
from time import gmtime, strftime, sleep, mktime
from wsgiref.handlers import format_date_time
from azure.common.client_factory import get_client_from_cli_profile
from azure.common.credentials import ServicePrincipalCredentials, UserPassCredentials
from azure.graphrbac import GraphRbacManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient

# JSON String ARM Template required for Function App. Do not alter
arm_template = "{\r\n    \"$schema\": \"https:\/\/schema.management.azure.com\/schemas\/2015-01-01\/deploymentTemplate.json#\",\r\n    \"contentVersion\": \"1.0.0.0\",\r\n    \"parameters\": {\r\n        \"functionAppName\": {\r\n            \"type\": \"string\",\r\n            \"metadata\": {\r\n                \"description\": \"The name of the function app that you wish to create.\"\r\n            }\r\n        },\r\n        \"EspExportStorageAccount\": {\r\n          \"type\": \"string\",\r\n          \"metadata\": {\r\n            \"description\": \"The connection string for the storage account that holds the activity logs.\"\r\n          }\r\n        },\r\n        \"espChannelURL\": {\r\n          \"type\": \"string\",\r\n          \"metadata\": {\r\n            \"description\": \"The URL for the ESP channel group.\"\r\n          }\r\n        },\r\n        \"storageAccountType\": {\r\n            \"type\": \"string\",\r\n            \"defaultValue\": \"Standard_LRS\",\r\n            \"allowedValues\": [\r\n                \"Standard_LRS\",\r\n                \"Standard_GRS\",\r\n                \"Standard_ZRS\",\r\n                \"Premium_LRS\"\r\n            ],\r\n            \"metadata\": {\r\n                \"description\": \"Storage Account type\"\r\n            }\r\n        }\r\n    },\r\n    \"variables\": {\r\n        \"functionAppName\": \"[parameters('functionAppName')]\",\r\n        \"EspExportStorageAccount\": \"[parameters('EspExportStorageAccount')]\",\r\n        \"espChannelURL\": \"[parameters('espChannelURL')]\",\r\n        \"hostingPlanName\": \"[parameters('functionAppName')]\",\r\n        \"storageAccountName\": \"[concat(uniquestring(resourceGroup().id), 'azfunctions')]\",\r\n        \"storageAccountid\": \"[concat(resourceGroup().id,'\/providers\/','Microsoft.Storage\/storageAccounts\/', variables('storageAccountName'))]\"\r\n    },\r\n    \"resources\": [\r\n        {\r\n            \"type\": \"Microsoft.Storage\/storageAccounts\",\r\n            \"name\": \"[variables('storageAccountName')]\",\r\n            \"apiVersion\": \"2015-06-15\",\r\n            \"location\": \"[resourceGroup().location]\",\r\n            \"properties\": {\r\n                \"accountType\": \"[parameters('storageAccountType')]\"\r\n            }\r\n        },\r\n        {\r\n            \"type\": \"Microsoft.Web\/serverfarms\",\r\n            \"apiVersion\": \"2015-04-01\",\r\n            \"name\": \"[variables('hostingPlanName')]\",\r\n            \"location\": \"[resourceGroup().location]\",\r\n            \"properties\": {\r\n                \"name\": \"[variables('hostingPlanName')]\",\r\n                \"computeMode\": \"Dynamic\",\r\n                \"sku\": \"Dynamic\"\r\n            }\r\n        },\r\n        {\r\n            \"apiVersion\": \"2015-08-01\",\r\n            \"type\": \"Microsoft.Web\/sites\",\r\n            \"name\": \"[variables('functionAppName')]\",\r\n            \"location\": \"[resourceGroup().location]\",\r\n            \"kind\": \"functionapp\",\r\n            \"dependsOn\": [\r\n                \"[resourceId('Microsoft.Web\/serverfarms', variables('hostingPlanName'))]\",\r\n                \"[resourceId('Microsoft.Storage\/storageAccounts', variables('storageAccountName'))]\"\r\n            ],\r\n            \"properties\": {\r\n                \"name\": \"[variables('functionAppName')]\",\r\n                \"serverFarmId\": \"[resourceId('Microsoft.Web\/serverfarms', variables('hostingPlanName'))]\",\r\n                \"siteConfig\": {\r\n                    \"appSettings\": [\r\n                        {\r\n                            \"name\": \"AzureWebJobsDashboard\",\r\n                            \"value\": \"[concat('DefaultEndpointsProtocol=https;AccountName=', variables('storageAccountName'), ';AccountKey=', listKeys(variables('storageAccountid'),'2015-05-01-preview').key1)]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"AzureWebJobsStorage\",\r\n                            \"value\": \"[concat('DefaultEndpointsProtocol=https;AccountName=', variables('storageAccountName'), ';AccountKey=', listKeys(variables('storageAccountid'),'2015-05-01-preview').key1)]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"WEBSITE_CONTENTAZUREFILECONNECTIONSTRING\",\r\n                            \"value\": \"[concat('DefaultEndpointsProtocol=https;AccountName=', variables('storageAccountName'), ';AccountKey=', listKeys(variables('storageAccountid'),'2015-05-01-preview').key1)]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"WEBSITE_CONTENTSHARE\",\r\n                            \"value\": \"[toLower(variables('functionAppName'))]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"FUNCTIONS_EXTENSION_VERSION\",\r\n                            \"value\": \"~1\"\r\n                        },\r\n                        {\r\n                            \"name\": \"WEBSITE_NODE_DEFAULT_VERSION\",\r\n                            \"value\": \"6.5.0\"\r\n                        },\r\n                        {\r\n                            \"name\": \"EspExportStorageAccount\",\r\n                            \"value\": \"[variables('EspExportStorageAccount')]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"espChannelURL\",\r\n                            \"value\": \"[variables('espChannelURL')]\"\r\n                        },\r\n                        {\r\n                            \"name\": \"appName\",\r\n                            \"value\": \"[variables('functionAppName')]\"\r\n                        }\r\n                    ]\r\n                }\r\n            }\r\n        }\r\n    ]\r\n}"

# ESP API Keys
esp_public_key = os.environ['ESP_ACCESS_KEY_ID']
esp_secret_key = os.environ['ESP_SECRET_ACCESS_KEY']

# Script Options.
options = {
    # The team id for which you the Azure subscriptions will be placed
    'esp_team_id': '', # Use Str '1' format
    'tenant_id': '',
    'script_service_principal_client_id': '',
    'script_service_principal_secret': '',
    # 'all' or an ['1', '2', '3'] array of  subscriptions ids as a white_list
    'subscriptions_to_onboard': 'all',
    # Array of subscriptions to skip for onboarding. Default: Empty Array
    'subscriptions_to_exclude': [],
    'logs_retention_time': '7',
    # Designate a subscription ID for the storage acct to be created to hold centralized logs for all subs
    # Or specify thte subscription that holds existing centralized logs if adding an additional subscription
    # after already setting up the Function App in an earlier onboarding run.
    'subscription_id_for_unified_logs': False,
    # If you're already exporting subscriptions activity logs to a an existing storage account, please
    # provide the information below.
    'existing_logs_storage_account_id': False,
    'existing_logs_storage_account_name': False,
    # False by default. When specified please use String format '00' This is only applicable when adding additional
    # accounts to an existing Azure Group in
    'esp_group_id': False,
    # Storage Key  would only be needed if you're already exporting logs to a Storage Account,
    # but haven't set up a function app for ESP. Do NOT set if only adding a
    # new subscription to an existing Azure ESP Group.
    'existing_logs_storage_account_key': False,
    # The 'Log Profile' is the configuration for exporting a subscription's
    # activity logs. There can only be a single Log Profile in a subscription
    # The 'dry-run option will let you know what subscriptions are already
    # exporting logs'
    'remove_existing_log_profile': True,
    # Script required, do not alter
    'template': arm_template,
    'dry_run': True
}


def main(options):
    # Check command line arguments. Defaults to --dry-run True
    parser = argparse.ArgumentParser(
        description='Onboard Azure Subscriptions to Evident.io')
    parser.add_argument('--dry-run')
    args = parser.parse_args()
    if args.dry_run == 'False':
        options['dry_run'] = False
    options['subscriptions_to_onboard'] = filter_subs_to_onboard(options)
    validate_subscriptions(options['subscriptions_to_onboard'])
    if options['dry_run'] == False:
        subscriptions = prepare_subscriptions(options)
        onboard_all_subscriptions(options, subscriptions)
    exit()


def onboard_all_subscriptions(options, subscriptions):
    # Create a new Storage Account for unified logs if there is not an
    # existing storage account for logs
    if options['subscription_id_for_unified_logs'] and options['existing_logs_storage_account_id'] == False:
        print('Creating ESP Azure Group')
        group = create_azure_group()
        logs_info = create_azure_logs_resources(
            options, options['subscription_id_for_unified_logs'], group['url'])
        storage_info = logs_info['storage_info']
        function_app_name = logs_info['function_app_name']
    elif options['subscription_id_for_unified_logs'] and options['existing_logs_storage_account_key']:
        print('Creating ESP Azure Group')
        group = create_azure_group()
        connection_string = create_connection_string(
            options['existing_logs_storage_account_name'], options['existing_logs_storage_account_key'])
        storage_info = {
            'connection_string': connection_string,
            'name': options['existing_logs_storage_account_name'],
            'id': options['existing_logs_storage_account_id'],
        }
        resource_group = create_resource_group(
            options['subscription_id_for_unified_logs'])
        function_app_name = build_function_app(options, options[
                                               'subscription_id_for_unified_logs'], resource_group, group['url'], storage_info)
    else:
        storage_info = {
            'id': options['existing_logs_storage_account_id'],
            'name': options['existing_logs_storage_account_name'],
        }
        group = {'id': options['esp_group_id']}
    # Register subs with ESP and create a Storage Account and Function App in
    # the designated subscription
    esp_accounts = []
    for sub in subscriptions:
        print('Registering ' + sub['sub_id'] + ' with ESP')
        esp_account = register_sub_with_esp(options, sub)
        if options['subscription_id_for_unified_logs']:
            # Add subscription to channel group
            print('Adding ESP Account to Group')
            add_subscription_to_group(group['id'], esp_account['data']['relationships'][
                                      'external_account']['data']['id'])
        else:
            print(
                'Creating individual Storage Account and Function App for subscription ' + sub['sub_id'])
            logs_info = create_azure_logs_resources(options, sub['sub_id'], esp_account[
                                                    'data']['attributes']['channel_url'])
            storage_info = logs_info['storage_info']
            esp_account['storage_info'] = logs_info['storage_info']
            esp_account['function_app_name'] = logs_info['function_app_name']
        esp_accounts.append(esp_account)
        print('Exporting logs to Storage Account')
        export_activity_logs_to_storage_account(
            options, sub['sub_id'], storage_info['id'])

    # Write Storage Account and Function App Info along with ESP Accounts info
    # to reference later into CSV
    print("Creating 'onboarding_results.csv' in current directory. ")
    datestring = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
    with open('onboarding_results' + datestring + '.csv', 'w') as file:
        writer = csv.writer(file, delimiter=',')
        if options['esp_group_id']:
            writer.writerow(
                ['Storage Account Name', 'Storage Account ID', 'ESP Azure Group ID'])
            writer.writerow(
                [storage_info['name'], storage_info['id'], group['id']])
            writer.writerow(['Subscription', 'ESP Account Name'])
            for acct in esp_accounts:
                writer.writerow([
                    acct['data']['attributes']['subscription_id'],
                    acct['included'][0]['attributes']['name']
                ])
        elif options['subscription_id_for_unified_logs']:
            writer.writerow(['Storage Account Name', 'Storage Account ID',
                             'Function App Name', 'ESP Azure Group ID', 'ESP Group URL'])
            writer.writerow([storage_info['name'], storage_info[
                            'id'], function_app_name, group['id'], group['url']])
            writer.writerow(['Subscription', 'ESP Account Name'])
            for acct in esp_accounts:
                writer.writerow([
                    acct['data']['attributes']['subscription_id'],
                    acct['included'][0]['attributes']['name']
                ])
        else:
            writer.writerow([
                'Subscription',
                'ESP Account Name',
                'Storage Account ID',
                'Storage Account Name',
                'Function App Name',
                'Channel URL'
            ])
            for acct in esp_accounts:
                writer.writerow([
                    acct['data']['attributes']['subscription_id'],
                    acct['included'][0]['attributes']['name'],
                    acct['storage_info']['id'],
                    acct['storage_info']['name'],
                    acct['function_app_name'],
                    acct['data']['attributes']['channel_url']
                ])

    print("Finished.")
    return

# For a dry run -- check for insights registration and existing log
# profiles on all subscriptions


def validate_subscriptions(subscriptions):
    results = []
    for subscription in subscriptions:
        # Check if insights is registered for subscription
        insights_registered_ = insights_registered(subscription)
        if insights_registered_ == False:
            print('Subscription ' + subscription +
                  ' does not have Microsoft Insights enabled. It may take up to an hour for this to be enabled during script run. ')
        log_profile = get_log_profile(subscription)
        if log_profile:
            print('Subscription ' + subscription +
                  ' has an existing log profile configured to export activity logs:')
            log_profile_exists = True
            log_profile_data = vars(log_profile)
        else:
            log_profile_exists = False
            log_profile_data = None
        subscription_result = {
            'id': subscription,
            'insights_registered': insights_registered_,
            'log_profile': log_profile_exists,
            'log_profile_configuration': log_profile_data
        }
        results.append(subscription_result)

    # Write Dry Run results
    print("Creating 'pre_onboarding_results.csv' in current directory. ")
    datestring = datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M-%S')
    with open('pre_onboarding_results' + datestring + '.csv', 'w') as file:
        writer = csv.writer(file, delimiter=',')
        writer.writerow(['Subscription', 'Insights Registered',
                         'Log Profile', 'Log Profile Configuration'])
        for result in results:
            writer.writerow([result['id'], result['insights_registered'], result[
                            'log_profile'], result['log_profile_configuration']])
    return

# Creates Service Principals, assigns permissions, and creates a csv of
# links to assist in granting permissions from console


def prepare_subscriptions(options):
    # Create service principals and save app links to CSV and prompt user to
    subscriptions = []
    for sub in options['subscriptions_to_onboard']:
        if insights_registered(sub) == False:
            register_msft_insights(sub)
        print('Creating Service Principal for ' + sub)
        sub_config = {'sub_id': sub}
        sub_config = create_app_registration(options, sub_config)
        sub_config = create_service_principal(options, sub_config)
        assign_roles_to_service_principal(sub_config)
        create_oauth_permissions_grant(options, sub_config)
        sub_config['client_id'] = sub_config['application'].app_id
        sub_config['secret_key'] = sub_config['secret_key']
        sub_config['principal_url'] = 'https://portal.azure.com/#blade/Microsoft_AAD_IAM/ApplicationBlade/objectId/' \
            + sub_config['application'].object_id + \
            '/appId/' + sub_config['application'].app_id
        subscriptions.append(sub_config)
    return subscriptions

# Checks and filters subscriptions to onboard
# based on include/exclude lists and subscription accessibility


def filter_subs_to_onboard(options):
    sub_client = get_client_from_cli_profile(
        SubscriptionClient, api_version='2016-06-01')
    # Get all accessible subscriptions
    all_accessible_subs = set([])
    subs_to_onboard = set([])
    for sub in sub_client.subscriptions.list():
        all_accessible_subs.add(sub.subscription_id)
    if options['subscriptions_to_onboard'] == 'all':
        subs_to_onboard = set(all_accessible_subs)
    else:
        subs_to_onboard = set(options['subscriptions_to_onboard'])
    subs_to_onboard = subs_to_onboard.difference(
        options['subscriptions_to_exclude'])
    return subs_to_onboard


def register_sub_with_esp(options, sub_config):
    method = 'POST'
    uri = '/api/v2/external_accounts/azure'
    timeout = 10
    body = {'data': {
        'attributes': {
            'name': str(uuid.uuid4()),
            'team_id': options['esp_team_id'],
            'subscription_id': sub_config['sub_id'],
            'tenant_id': options['tenant_id'],
            'client_id': sub_config['client_id'],
            'app_key': sub_config['secret_key']
        }}}
    data = json.dumps(body)
    count = 0
    register_successful = False
    while register_successful == False and count < 20:
        response = esp_api_call(method, uri, data, timeout)
        count += 1
        sleep(60)
        try:
            validate_response = response['data']
            return response
        except:
            pass
    if register_successful == False:
        print('There was an issue registering Subscription ' + sub_config['sub_id'] + ' with ESP. ')
    return


def create_azure_group():
    method = 'POST'
    uri = '/api/v2/azure_groups'
    name = str(uuid.uuid4())
    timeout = 10
    body = {'data': {
        'attributes': {
            'name': name
        }}}
    data = json.dumps(body)
    response = esp_api_call(method, uri, data, timeout)
    group = {'id': response['data']['id'],
             'url': response['data']['attributes']['url']}
    return group


def get_accounts_in_azure_group(group_id):
    method = 'GET'
    uri = '/api/v2/external_accounts.json?filter%5Bazure_group_id_eq%5D=' + \
        str(group_id)
    timeout = 10
    body = ''
    data = json.dumps(body)
    response = esp_api_call(method, uri, data, timeout)
    accts = []
    for acct in response['data']:
        accts.append(int(acct['id']))
    return accts


def add_subscription_to_group(group_id, acct_id):
    acct_id = int(acct_id)
    acct_ids = get_accounts_in_azure_group(group_id)
    acct_ids.append(acct_id)
    method = 'PATCH'  # Might be patch
    uri = '/api/v2/azure_groups/' + str(group_id)
    timeout = 10
    body = {'data': {
        'attributes': {
            'external_account_ids': acct_ids
        }}}
    data = json.dumps(body)
    response = esp_api_call(method, uri, data, timeout)
    return response


def esp_api_call(method, uri, data, timeout):
    url = 'https://api.evident.io'
    now = datetime.now()
    stamp = mktime(now.timetuple())
    dated = format_date_time(stamp)
    hex = hashlib.md5(data.encode('UTF-8')).hexdigest()
    body = codecs.encode(codecs.decode(hex, 'hex'),
                         'base64').decode().rstrip('\n')
    canonical = '%s,%s,%s,%s,%s' % (
        method, 'application/vnd.api+json', body, uri, dated)
    secret = bytes(esp_secret_key, 'UTF-8')
    canonical = bytes(canonical, 'UTF-8')
    hashed = hmac.new(secret, canonical, hashlib.sha1)
    encoded = base64.b64encode(hashed.digest())
    auth = str(encoded, 'UTF-8')
    headers = {'Date': '%s' % (dated),
               'Content-MD5': '%s' % (body),
               'Content-Type': 'application/vnd.api+json',
               'Accept': 'application/vnd.api+json',
               'Authorization': 'APIAuth %s:%s' % (esp_public_key, auth)}
    count = 0
    response_received = False
    while response_received == False and count < 100:
        sleep(10)
        count += 1
        try:
            r = requests.Request(method, url + uri, data=data, headers=headers)
            p = r.prepare()
            s = requests.Session()
            ask = s.send(p, timeout=timeout)
            response = ask.json()
            return response
        except:
            pass
    if response_received == False:
        print("There was an issue reaching the ESP API. ")
    return

# Creates Azure Application Registration from which a Service Principal
# will be created


def create_app_registration(options, sub_config):
    credentials = ServicePrincipalCredentials(
        tenant=options['tenant_id'],
        client_id=options['script_service_principal_client_id'],
        secret=options['script_service_principal_secret'],
        resource='https://graph.windows.net'
    )
    rbac_client = GraphRbacManagementClient(
        credentials, tenant_id=options['tenant_id'])
    app_name = 'Evident-io-sub-' + \
        sub_config['sub_id'] + '-id-' + str(uuid.uuid1())[:6]
    app_url = 'https://evident.io'
    app_uri = app_url + '/' + app_name
    # Create Application
    sub_config['application'] = rbac_client.applications.create({
        'display_name': app_name,
        'home_page': app_url,
        'identifier_uris': [app_uri],
        'available_to_other_tenants': False
    })
    # Handle retries on this
    update_required_permissions_for_app(
        credentials, options['tenant_id'], sub_config['application'].object_id)
    return sub_config

# Specifies the required permissions for the service principal but does
# not grant the permissions


def update_required_permissions_for_app(credentials, tenant_id, app_object_id):
    auth_header = credentials.token['access_token']
    headers = {'Authorization': auth_header,
               'Content-Type': 'application/json'}
    url = 'https://graph.windows.net/' + tenant_id + \
        '/applications/' + app_object_id + '?api-version=1.6'
    body = {'requiredResourceAccess': [
            {
                "resourceAppId": "00000003-0000-0000-c000-000000000000",
                "resourceAccess": [
                    {
                        "id": "df021288-bdef-4463-88db-98f22de89214",
                        "type": "Role"
                    }
                ]
            },
            {
                "resourceAppId": "00000002-0000-0000-c000-000000000000",
                "resourceAccess": [
                    {
                        "id": "5778995a-e1bf-45b8-affa-663a9f3f4d04",
                        "type": "Role"
                    },
                    {
                        "id": "c582532d-9d9e-43bd-a97c-2667a28ce295",
                        "type": "Scope"
                    }
                ]
            }
            ]
            }
    data = json.dumps(body)
    count = 0
    required_permissions_updated = False
    while required_permissions_updated == False and count < 20:
        count += 1
        sleep(3)
        try:
            response = requests.patch(url, headers=headers, data=data)
            required_permissions_updated = True
        except:
            pass
    return

# Creates Azure application and service principal for an azure subscription


def create_service_principal(options, sub_config):
    credentials = ServicePrincipalCredentials(
        tenant=options['tenant_id'],
        client_id=options['script_service_principal_client_id'],
        secret=options['script_service_principal_secret'],
        resource='https://graph.windows.net'
    )
    rbac_client = GraphRbacManagementClient(
        credentials, tenant_id=options['tenant_id'])
    # Create Service Principal
    current_time = datetime.now(timezone.utc)
    key = {
        'start_date': current_time.isoformat(),
        'end_date': current_time.replace(year=current_time.year + 3).isoformat(),
        'key_id': str(uuid.uuid4()),
        'value': str(uuid.uuid4())
    }
    sub_config['secret_key'] = key['value']
    sub_config['service_principal'] = rbac_client.service_principals.create({
        'app_id': sub_config['application'].app_id,
        'account_enabled': True,
        'password_credentials': [key]
    })
    return sub_config


def get_service_principal(credentials, tenant, app_id):
    filter = "appID eq '" + app_id + "'"
    rbac_client = GraphRbacManagementClient(credentials, tenant_id=tenant)
    principals = rbac_client.service_principals.list(filter=filter)
    object_id = ''
    for principal in principals:
        object_id = principal.object_id
    return object_id


def create_oauth_permissions_grant(options, sub_config):
    # Get Credentials for this function
    credentials = ServicePrincipalCredentials(
        tenant=options['tenant_id'],
        client_id=options['script_service_principal_client_id'],
        secret=options['script_service_principal_secret'],
        resource='https://graph.windows.net'
    )
    tenant = options['tenant_id']
    service_principal_object_id = sub_config['service_principal'].object_id
    # Get service principal object ids for Azure built-in AAD and Graph roles
    # This is required before creating the Oauth2 tokens
    aad_app_id = '00000002-0000-0000-c000-000000000000'
    graph_app_id = '00000003-0000-0000-c000-000000000000'
    aad_object_id = get_service_principal(credentials, tenant, aad_app_id)
    graph_api_object_id = get_service_principal(
        credentials, tenant, graph_app_id)
    # Make REST calls to grant Oauth2 tokens for both AAD and Graph for the
    # service principal
    token = credentials.token['access_token']
    url = 'https://graph.windows.net/myorganization/oauth2PermissionGrants?api-version=1.6'
    headers = {'Authorization': 'Bearer ' +
               token, 'Content-Type': 'application/json'}
    # Call for AAD
    aad_body = {
        "odata.type": "Microsoft.DirectoryServices.OAuth2PermissionGrant",
        "clientId": service_principal_object_id,
        "consentType": "AllPrincipals",
        "principalId": None,
        "resourceId": aad_object_id,
        "scope": "User.Read.All Directory.Read.All",
        "startTime": "0001-01-01T00:00:00",
        "expiryTime": "9000-01-01T00:00:00"
    }
    data = json.dumps(aad_body)
    response = requests.post(url, headers=headers, data=data)
    print("Attempting to grant AAD permissions: " + str(response.status_code))
    # Call for Graph
    graph_body = {
        "odata.type": "Microsoft.DirectoryServices.OAuth2PermissionGrant",
        "clientId": service_principal_object_id,
        "consentType": "AllPrincipals",
        "principalId": None,
        "resourceId": graph_api_object_id,
        "scope": "User.Read.All",
        "startTime": "0001-01-01T00:00:00",
        "expiryTime": "9000-01-01T00:00:00"
    }
    data = json.dumps(graph_body)
    response = requests.post(url, headers=headers, data=data)
    print("Attempting to grant Graph permissions: " + str(response.status_code))

    return


# Assigns Roles to service principal for API reader role & storage
# account key operator role

def assign_roles_to_service_principal(sub_config):
    # Create Client and define role ids & scope to add to service principal
    auth_mgmt_client = get_client_from_cli_profile(
        AuthorizationManagementClient)
    scope = '/subscriptions/' + sub_config['sub_id']
    reader_role_id = '/subscriptions/' + \
        sub_config[
            'sub_id'] + '/providers/Microsoft.Authorization/roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7'
    storage_key_operator_role_id = '/subscriptions/' + \
        sub_config[
            'sub_id'] + '/providers/Microsoft.Authorization/roleDefinitions/81a9662b-bebf-436f-a333-f67b29880f12'

    reader_role_granted = False
    count = 0
    while reader_role_granted == False and count <= 0:
        sleep(3)
        try:
            # Grant API Management Service Reader Role to subscription
            response = auth_mgmt_client.role_assignments.create(
                scope,
                str(uuid.uuid4()),
                properties={
                    'principal_id': sub_config['service_principal'].object_id,
                    'role_definition_id': reader_role_id
                })
            reader_role_granted = True
        except:
            pass
    storage_role_granted = False
    count = 0
    while storage_role_granted == False and count <= 0:
        sleep(3)
        try:
            # Grant Storage Account Key Operator Role to subscription
            response = auth_mgmt_client.role_assignments.create(
                scope,
                str(uuid.uuid4()),
                properties={
                    'principal_id': sub_config['service_principal'].object_id,
                    'role_definition_id': storage_key_operator_role_id
                })
            storage_role_granted = True
        except:
            pass
    return sub_config


def create_azure_logs_resources(options, subscription, channel_url):
    print("Creating Resource Group")
    resource_group = create_resource_group(subscription)
    print('Creating Storage Account for logs')
    storage_info = create_storage_account(subscription, resource_group)
    print('Creating Function App')
    function_app_name = build_function_app(
        options, subscription, resource_group, channel_url, storage_info)
    logs_info = {
        'function_app_name': function_app_name,
        'storage_info': storage_info
    }
    return logs_info

# This creates the storage account that will hold Azure subscription(s)
# activity logs


def create_storage_account(subscription_id, resource_group):
    stg_client = get_client_from_cli_profile(
        StorageManagementClient, subscription_id=subscription_id)
    # the stg acct name must be globally unique in Azure
    name_availability = False
    while name_availability == False:
        stg_acct_name = generate_storage_account_name()
        name_availability = stg_client.storage_accounts.check_name_availability(
            stg_acct_name)
    # Create Storage Account
    resp = stg_client.storage_accounts.create(
        resource_group,  # resource group name
        stg_acct_name,  # account name
        parameters={
            'sku': {'name': 'Standard_LRS'},
            'kind': 'Storage',
            'location': 'West US',
            'enable_https_traffic_only': True
        }
    )
    # The storage account takes a few moments to be provisioned
    stg_acct_provisioned = stg_client.storage_accounts.get_properties(
        resource_group, stg_acct_name).provisioning_state
    while stg_acct_provisioned.value != 'Succeeded':
        print('Waiting for Storage Account to be provisioned')
        sleep(10)
        stg_acct_provisioned = stg_client.storage_accounts.get_properties(
            resource_group, stg_acct_name).provisioning_state
    # Grab the key and assemble the connection string
    stg_acct_key = stg_client.storage_accounts.list_keys(
        resource_group, stg_acct_name).keys[0].value
    stg_acct_connection_string = create_connection_string(
        stg_acct_name, stg_acct_key)
    stg_acct_id = stg_client.storage_accounts.get_properties(
        resource_group, stg_acct_name).id
    storage_info = {
        'name': stg_acct_name,
        'connection_string': stg_acct_connection_string,
        'id': stg_acct_id
    }
    return storage_info


def create_connection_string(stg_acct_name, stg_acct_key):
    connection_string = 'DefaultEndpointsProtocol=https;AccountName=' + \
        stg_acct_name + ';AccountKey=' + stg_acct_key + ';EndpointSuffix=core.windows.net'
    return connection_string

# Launch ARM Templates to create the resources for event driven alerts:


def build_function_app(options, subscription_id, resource_group, channel_url, storage_info):
    app_name = deploy_function_app_template(
        resource_group, options['template'],
        channel_url,
        storage_info['connection_string'],
        subscription_id
    )
    # Credentials for uploading app function files
    credentials = ServicePrincipalCredentials(
        tenant=options['tenant_id'],
        client_id=options['script_service_principal_client_id'],
        secret=options['script_service_principal_secret'],
        resource='https://management.core.windows.net/'
    )
    password = get_function_app_deploy_password(
        credentials, subscription_id, app_name, resource_group)
    response = upload_function_app_zip(app_name, password)
    return app_name

# This launches the ARM template that creates the Function App container
# and associated storage account


def deploy_function_app_template(resource_group, template, channel_url, storage_logs_connection_string, subscription_id):
    print('Deploying Function App ARM Template')
    resource_client = get_client_from_cli_profile(
        ResourceManagementClient, subscription_id=subscription_id)
    template = json.loads(template)
    deployment_name = 'espFunctionDeploy'
    app_name = str(uuid.uuid4()).replace(
        '-', '')[:8] + '-evident-esp-trigger-' + str(uuid.uuid4()).replace('-', '')[:8]
    storage_connection_string = storage_logs_connection_string
    esp_channel_url = channel_url
    parameters = {
        'functionAppName': {'value': app_name},
        'EspExportStorageAccount': {'value': storage_connection_string},
        'espChannelURL': {'value': esp_channel_url}
    }
    deployment = resource_client.deployments.create_or_update(
        resource_group,
        deployment_name,
        properties={
            'template': template,
            'parameters': parameters,
            'mode': 'Incremental'
        }
    )
    return app_name

# Uploads function handler JS file and other required files


def upload_function_app_zip(func_app_name, func_app_deploy_pass):
    print('Uploading Function App required files zip. ')
    url = 'https://' + func_app_name + '.scm.azurewebsites.net'
    uri = '/api/zip/site/wwwroot'
    url = url + uri
    data = open('esp-events-trigger.zip', 'rb')
    headers = {'Content-Type': 'application/octet-stream'}
    user = '$' + func_app_name
    password = func_app_deploy_pass
    count = 0
    upload_request_successful = False
    response = ''
    while upload_request_successful == False and count < 25:
        sleep(10)
        count += 1
        try:
            response = requests.put(url, auth=(user, password),
                                    headers=headers, data=data)
            upload_request_successful = True
        except:
            pass
    if upload_request_successful == False:
        response = 'Could not connect to Function App to upload files.'
    return response

# To upload the function app files you must first retrieve function app
# specific credentials


def get_function_app_deploy_password(credentials, subscription, func_app_name, resource_group):
    auth_header = credentials.token['access_token']
    headers = {'Authorization': 'Bearer ' + auth_header,
               'Content-Type': 'application/xml'}
    url = 'https://management.azure.com/subscriptions/' + subscription + '/resourceGroups/' + \
        resource_group + '/providers/Microsoft.Web/sites/' + \
        func_app_name + '/publishxml?api-version=2016-08-01'
    creds_received = False
    count = 0
    password = ''
    print('Retrieving the Function App credentials to upload source zip file. ')
    while creds_received == False and count <= 120:
        sleep(20)
        count += 1
        try:
            response = requests.post(url, headers=headers)
            publish_creds_xml = xmltodict.parse(response.content)
            password = publish_creds_xml['publishData'][
                'publishProfile'][0]['@userPWD']
            return password
        except:
            pass
    if creds_received == False:
        print('There was an issue obtaining credentials to publish the function app')
    return

# Creates a resource group that will hold the Storage Account and Function
# App for event driven alerts


def create_resource_group(subscription_id):
    print('Creating Azure Resource Group')
    resource_client = get_client_from_cli_profile(
        ResourceManagementClient, subscription_id=subscription_id)
    name = 'evident-io' + str(uuid.uuid4())[:8]
    resource_group = resource_client.resource_groups.create_or_update(
        name,
        parameters={
            'name': name,
            'location': 'West US'
        }
    )
    return name


# Azure Storage Account's must have a globally unique name

def generate_storage_account_name():
    unique_val = str(uuid.uuid4())[:12]
    unique_val = unique_val.replace('-', '')
    stg_acct_name = 'evidentlogs' + unique_val
    return stg_acct_name

# Check for an existing Azure Log profile


def get_log_profile(subscription):
    log_client = get_client_from_cli_profile(
        MonitorManagementClient, subscription_id=subscription)
    logs = log_client.log_profiles.list()
    log_profile = ''
    for log in logs:
        log_profile = log
    if log_profile:
        return log_profile
    else:
        return False
    return

# Creates a Log Profile for the subscription to export activity logs.
# Also registers Microsoft Insights for the subscription as this is a
# pre-req for a Log Profile


def export_activity_logs_to_storage_account(options, subscription, storage_account_id):
    log_client = get_client_from_cli_profile(
        MonitorManagementClient, subscription_id=subscription)
    resource_client = get_client_from_cli_profile(
        ResourceManagementClient, subscription_id=subscription)
    # Make sure insights is registered, if not, register it
    while insights_registered(subscription) == False:
        sleep(60)
        insights = resource_client.providers.get('microsoft.insights')
        print(insights.registration_state)
        print('Waiting for Microsoft Insights to register -- ' +
              strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    # Check for existing log profile and if allowed, remove it.
    existing_log_profile = get_log_profile(subscription)
    if existing_log_profile and options['remove_existing_log_profile'] == False:
        print("Subscription " + subscription +
              " has an existing log profile. Activity logs will not be exported. ")
        return
    elif existing_log_profile and options['remove_existing_log_profile'] == True:
        print('Removing log profile for subscription ' + subscription)
        resp = log_client.log_profiles.delete(existing_log_profile.name)
    # Create Log Profile
    name = 'default'
    log_profile_created = False
    count = 0
    while log_profile_created == False and count < 25:
        sleep(5)
        count += 1
        try:
            log_profile = log_client.log_profiles.create_or_update(
                name,
                parameters={
                    'location': 'global',
                    'locations': [
                        'australiaeast', 'australiasoutheast', 'brazilsouth',
                        'canadacentral', 'canadaeast', 'centralindia', 'centralus',
                        'eastasia', 'eastus', 'eastus2', 'japaneast', 'japanwest',
                        'koreacentral', 'koreasouth', 'northcentralus', 'northeurope',
                        'southcentralus', 'southindia', 'southeastasia', 'uksouth',
                        'ukwest', 'westcentralus', 'westeurope', 'westindia', 'westus',
                        'westus2', 'global'
                    ],
                    'categories': ['Write', 'Delete', 'Action'],
                    'storage_account_id': storage_account_id,
                    'retention_policy': {
                        'enabled': True,
                        'days': int(options['logs_retention_time'])
                    }
                })
            log_profile_created = True
        except:
            pass
    if log_profile_created == False:
        print('Logs could not be exported for subscription ID: ' + subscription)
    return

# Microsoft Insights must be registered in order to export activity logs to a storage account.
# This checks if Insight's is registered or not for a subscription.


def insights_registered(subscription):
    # Check if insights is registered for subscription
    resource_client = get_client_from_cli_profile(
        ResourceManagementClient, subscription_id=subscription)
    insights = resource_client.providers.get('microsoft.insights')
    if insights.registration_state == 'Registered':
        return True
    else:
        return False
    return

# Registering Microsoft Insights can take as long as an hour per
# subscription to complete.


def register_msft_insights(subscription):
    resource_client = get_client_from_cli_profile(
        ResourceManagementClient, subscription_id=subscription)
    if resource_client.providers.get('microsoft.insights') != 'Registering':
        insights = resource_client.providers.register('microsoft.insights')
        print("Registering Microsoft Insights for subscription: " + subscription)
        print("This may take up to an hour per subscription -- " +
              strftime("%Y-%m-%d %H:%M:%S", gmtime()))
    return

if __name__ == '__main__':
    main(options)
