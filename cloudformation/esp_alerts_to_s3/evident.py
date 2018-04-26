from __future__ import print_function

import json
import re
import boto3
import os
from datetime import datetime


# Global Variables from Lambda Environment Variables
DEBUGGING = os.environ.get("DEBUGGING", "false").lower()
STREAMNAME = os.environ.get("STREAMNAME", None)
bucket_name = os.environ.get("TARGETS3", None)
folder = os.environ.get("TARGETS3PREFIX", None)


#############################################
# Inputs: Takes 2 printable Inputs
# Action: Prints Title then item_to_print if Global variable debugging is set to True
# Returns: null
##############################################
def debugging(title, item_to_print):
	if(DEBUGGING == "true"):
		print(title)
		print(item_to_print)
	return


#############################################
# Inputs: Takes JSON object
# Action: write the JSON string as a record on the Firehose
# Returns: Boolean
##############################################
def write_to_kinesis_firehose(message):

	firehose = boto3.client('firehose')
	response = firehose.put_record(
		DeliveryStreamName=STREAMNAME,
			Record={
			'Data': (json.dumps(message) + "\n")
			}
		)

	if response['ResponseMetadata']['HTTPStatusCode'] != 200:
		print("Failed to put " + message)
		return False

	debugging("Kinesis Firehose Put Status", response)
	print('Alert sent to Firehose Successfully.')
	return True


#############################################
# Inputs: Takes JSON object
# Action: Format JSON object
# Returns: JSON object
#
#############################################
def format_alert(alert):
	return alert


#############################################
# Lambda Entry Point
#############################################
def lambda_handler(event, context):

	debugging("Message",event)

	# Getting ESP alert message
	message = event['Records'][0]['Sns']['Message']
	alert = json.loads(message)
	debugging("RAW Alert Message", alert)

	formatted_alert = format_alert(alert)
	debugging("Formatted Alert", alert)
	return write_to_kinesis_firehose(formatted_alert)

	
