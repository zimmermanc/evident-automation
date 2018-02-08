import json
import csv
import uuid
import time
import esp
import boto3
###################################
# REQUIREMENTS:
# - PYTHON 3
# - ESP SDK: to install run 'pip install esp'
# - BOTO3: to install run 'pip install boto3'
# - Set AWS Credentials (not required when inputing CSV of pre-configured ARNs):
#    1) run 'pip install awscli'
#    2) run 'awscli configure'
# - Set ESP SDK Credentials as environment variables:
#   https://esp.evident.io/settings/api_keys
#    1) run 'export ESP_ACCESS_KEY_ID=$access_key_from_above_link'
#    2) run 'export ESP_SECRET_ACCESS_KEY=$secret_access_key_from_above_link'
# - In the 'Options' field below, please choose whether you would like to
#    1) Add the aws account to ESP by choosing 'True/False' for onboard_account
#    2) Enable User Attribution for this account.
# - If you choose ONLY to enable user attribution for an existing ESP account
#    please specify the 'account_name' field as well
# - When above requirements satisfied, run 'python3 main.py'

options = {

    # User Config Options

    # Bulk Onboarding of AWS accounts that already have IAM resources setup
    # The CSV should be structured as follows: 
    #     name, ARN, external_id
    # You must also specify the name of the ESP Team to place these AWS accounts in
    'accounts_csv_filename': False, # Filename location for the CSV
    'team_name': 'Default Team', 

    # When onboarding an AWS account with no pre-configured IAM resources
    'onboard_account': False,
    'enable_ua': False,
    'account_name': False,

    # Script required parameters, do not alter
    'base_stack_name': 'EvidentIO',
    'base_template_url': 'https://s3-us-west-2.amazonaws.com/esp-onboarding/esp_add_account.json',
    'ua_stack_name': 'EvidentIOUA',
    'ua_template_url': 'https://s3-us-west-2.amazonaws.com/esp-onboarding/esp_enable_ua.json',
    'external_id': None,
    'esp_ua_endpoint': None,
    'cloudtrail_name': None,
    'esp_role_name': None,
    'esp_role_arn': None,
    'esp_account_id': None
}


def main(options):

    print('Starting...')
    if options['accounts_csv_filename'] != False:
        options['team_id'] = get_team_id(options['team_name'])
        results = register_arns_from_csv(options)
        # Write Results to additional_csv

    if options['onboard_account'] == True:
        options['team_id'] = get_team_id(options['team_name'])
        options['external_id'] = str(uuid.uuid4())
        options = create_esp_stack(options)
        options = register_esp(options)

    if options['enable_ua'] == True:
        options = get_ua_endpoint(options)
        options = create_ua_stack(options)
        register_ua(options)

    exit()


# ESP requires that you specify which ESP 'Team' to add 
# a new AWS Account to

def get_team_id(team_name):
    response = esp.Team.where(name_eq=team_name)

    if 'errors' in response:
        exit(response.errors)

    if len(response) < 1:
        exit("Cannot find Team ID for team name: {}".format(team_name))
    else:
        print("Team ID: {}".format(response[0].id_))
        return response[0].id_  # the SDK uses id_ instead of id to avoid


# Get the SNS Endpoint from ESP required when setting up
# resources in AWS for User Attribution

def get_ua_endpoint(options):
    acct = None
    if options['esp_account_id'] == None:
        acct = esp.ExternalAccount.where(name_eq=options['account_name'])[0]
        role_name_end = len(acct.arn)
        role_name_start = (acct.arn.find('/') + 1)
        role_name = acct.arn[role_name_start:role_name_end]
        options['esp_role_name'] = role_name
        options['esp_account_id'] = acct.id_
        options['esp_role_arn'] = acct.arn
    else:
        acct = esp.ExternalAccount.find(options['esp_account_id'])
    acct.destroy_ua_endpoint()
    response = acct.create_ua_endpoint()
    options['esp_ua_endpoint'] = response["data"]["attributes"]["url"]
    return options


# Register User Attribution with ESP

def register_ua(options):
    acct_id = options['esp_account_id']
    cloudtrail_name = options['cloudtrail_name']
    acct = esp.ExternalAccount.find(acct_id)
    response = acct.update_cloudtrail_name(cloudtrail_name)
    print(response)
    print("User Attribution has been configured for account: {}.".format(
        options['account_name']))
    return

# Register an AWS Account with ESP using the IAM Role and External ID

def register_esp(options):
    response = esp.ExternalAccount.create(
        name=options['account_name'],
        arn=options['esp_role_arn'],
        external_id=options['external_id'],
        team_id=options['team_id']
    )

    if response._attributes == None:
        options['esp_account_id'] = "Error registering AWS Account! Please check the Evident Service IAM Role and Policy. "
    else:
        print("Account {} has been added.".format(options['account_name']))
        options['esp_account_id'] = response.id_
    return options


def register_arns_from_csv(options):
    results = []

    # Open CSV and attempt to register AWS Accounts within 

    with open(options['accounts_csv_filename'], newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            aws_acct = {}
            aws_acct['account_name'] = row[0]
            aws_acct['esp_role_arn'] = row[1]
            aws_acct['external_id'] = row[2]
            aws_acct['team_id'] = options['team_id']
            aws_acct['esp_account_id'] = register_esp(aws_acct)['esp_account_id']
            time.sleep(10)
            results.append(aws_acct)

    # Store results in CSV
    with open('results_esp_onboarding.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        for acct in results:
            writer.writerow(
                [
                    acct['account_name'],
                    acct['esp_role_arn'], 
                    acct['esp_account_id']
                ]
            )

    return



################################################
# For registerting an AWS account in ESP
# Creates an IAM Role and Policy
# AWS credential required
# See https://boto3.readthedocs.io/en/latest/guide/quickstart.html


def create_esp_stack(options):
    cfn_client = boto3.client('cloudformation')

    # non-blocking calls. AWS returns stack creation metadata
    response = cfn_client.create_stack(
        StackName=options['base_stack_name'],
        TemplateURL=options['base_template_url'],
        Parameters=[
            {
                'ParameterKey': 'EspExternalId',
                'ParameterValue': options['external_id']
            }
        ],
        # required since CFN will create an IAM role
        Capabilities=['CAPABILITY_IAM'],
        OnFailure='DELETE',
        Tags=[]
    )

    stack_id = response['StackId']
    print("Creating Stack {}".format(stack_id))

    # Checking every 2 seconds to see if the stack is completed
    stack_status = None
    while stack_status != 'CREATE_COMPLETE':
        time.sleep(2)
        stack_info = cfn_client.describe_stacks(
            StackName=stack_id)['Stacks'][0]
        stack_status = stack_info['StackStatus']

        if stack_info in ['CREATE_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_COMPLETE']:
            exit("Stack {} Creation Failed ".format(stack_status))
        elif stack_status == 'CREATE_COMPLETE':
            for output in stack_info['Outputs']:
                if output['OutputKey'] == 'EvidentIAMServiceRoleARN':
                    options['esp_role_arn'] = output['OutputValue']
                    role_name_end = len(output['OutputValue'])
                    role_name_start = (output['OutputValue'].find('/') + 1)
                    role_name = output['OutputValue'][
                        role_name_start:role_name_end]
                    options['esp_role_name'] = role_name
            return options
        else:
            print("Waiting.... Current Status: {}".format(stack_status))

################################################
# CREATE Cloudformation Stack
# For enabling User Attribution
# AWS credential required
# See https://boto3.readthedocs.io/en/latest/guide/quickstart.html


def create_ua_stack(options):
    cfn_client = boto3.client('cloudformation')
    ct_client = boto3.client('cloudtrail')

    # non-blocking calls. AWS returns stack creation metadata
    response = cfn_client.create_stack(
        StackName=options['ua_stack_name'],
        TemplateURL=options['ua_template_url'],
        Parameters=[
            {
                'ParameterKey': 'EvidentUAEndpoint',
                'ParameterValue': options['esp_ua_endpoint']
            },
            {
                'ParameterKey': 'EspServiceRoleName',
                'ParameterValue': options['esp_role_name']
            }
        ],
        # required since CFN will create an IAM role
        Capabilities=['CAPABILITY_IAM'],
        OnFailure='DELETE',
        Tags=[]
    )

    stack_id = response['StackId']
    print("Creating Stack {}".format(stack_id))

    # Checking every 2 seconds to see if the stack is completed
    stack_status = None
    while stack_status != 'CREATE_COMPLETE':
        time.sleep(2)
        stack_info = cfn_client.describe_stacks(
            StackName=stack_id)['Stacks'][0]
        stack_status = stack_info['StackStatus']

        if stack_info in ['CREATE_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_COMPLETE']:
            exit("Stack {} Creation Failed ".format(stack_status))
        elif stack_status == 'CREATE_COMPLETE':
            resource = cfn_client.describe_stack_resource(
                StackName=stack_id, LogicalResourceId="EvidentUATrail")
            ct_name = resource["StackResourceDetail"]["PhysicalResourceId"]
            # Set Cloudtrail to log 'WriteOnly' events as this is required.
            # this attribute is not available in the CFM templates
            response = ct_client.put_event_selectors(
                TrailName=ct_name,
                EventSelectors=[
                    {
                        'ReadWriteType': 'WriteOnly',
                        'IncludeManagementEvents': True,
                        'DataResources': []
                    }
                ]
            )
            options['cloudtrail_name'] = ct_name
            return options
        else:
            print("Waiting.... Current Status: {}".format(stack_status))

if __name__ == '__main__':
    main(options)
