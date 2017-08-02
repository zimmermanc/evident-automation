#Copyright (c) 2013, 2014, 2015, 2016, 2017. Evident.io (Evident). All Rights Reserved. 
#
#  Evident.io shall retain all ownership of all right, title and interest in and to 
#  the Licensed Software, Documentation, Source Code, Object Code, and API's ("Deliverables"), 
#  including (a) all information and technology capable of general application to Evident.io's
#  customers; and (b) any works created by Evident.io prior to its commencement of any
#  Services for Customer.

#Upon receipt of all fees, expenses and taxes due in respect of the relevant Services, 
#  Evident.io grants the Customer a perpetual, royalty-free, non-transferable, license to 
#  use, copy, configure and translate any Deliverable solely for internal business operations
#  of the Customer as they relate to the Evident.io platform and products, and always
#  subject to Evident.io's underlying intellectual property rights.
#
#IN NO EVENT SHALL EVIDENT.IO BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL, 
#  INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF 
#  THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF EVIDENT.IO HAS BEEN HAS BEEN
#  ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#EVIDENT.IO SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#  THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. 
#  THE SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED "AS IS". 
#  EVIDENT.IO HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS,
#  OR MODIFICATIONS.

# Works with ESP signature EC2-002. Whenever a global ingress rule is detected by EC2-002 this lambda function can be triggered
# using an SNS integration to revoke the egress rule.
from __future__ import print_function

import json
import re
import boto3

print('Loading function')

def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']

    alert = json.loads(message)
    data = alert['data']
    included = alert['included']

    for i in included:
        type = i['type']
        if type == "regions":
            regions = i
        if type == "metadata":
            metadata = i


    region = re.sub('_','-',regions['attributes']['code'])
    nacl_id = metadata['attributes']['data']['details']['networkAclId']
    offending_nacl_rules = metadata['attributes']['data']['details']['condition']

    remediation_out=0

    for nacl_rule in offending_nacl_rules:
        rule_number = nacl_rule['ruleNumber']
        rule_action = nacl_rule['ruleAction']
        rule_egress = nacl_rule['egress']
        if(rule_action=='allow'):
            print("Autoremediating nacl " + nacl_id , "rule number " + str(rule_number))
            remediation_out= auto_remediate_nacl_rule(region,nacl_id,rule_number,rule_egress)
            print(remediation_out)
    return remediation_out

def auto_remediate_nacl_rule(region,nacl_id, rule_num, rule_egress):
    ec2 = boto3.client('ec2',region_name=region)
    status = ec2.delete_network_acl_entry(NetworkAclId=nacl_id, RuleNumber=rule_num, Egress=rule_egress)
    return status
