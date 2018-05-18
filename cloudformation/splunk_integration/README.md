# ESP Splunk Integration

The following cloudformation template provides basic setup for setting up Splunk integration

## Option 1 - Using SNS + Lambda (preferred)
Template file: `esp_sns_integration_lambda_splunk.json`

The template produces the following resources:
- SNS Topic to receive ESP Alerts
- IAM role which allows ESP to assume role and push message to the SNS Topic
- SNS-invoked Lambda function which pushes the message to Splunk HTTP Event Collector

In order to launch this template, you will need to supply the following parameters:
- **SourceCodeBucket** and **SourceCodeKeyPath**. 
  You can puse the default value if you launch the stack in us-west-2 (oregon). 
  Otherwise, upload the **esp_splunk_lambda.zip** to an S3 bucket and update the parameter
- **SplunkHttpCollectorUrl** and **SplunkHttpcollectorToken**
  To create a new HEC Token:
  - Go to Splunk's indexer/Heavy forwarder
  - Settings -> Data Inputs -> HTTP Event Collector -> New Token
  - Index: esp (app's default index)
  - Leave the source and sourcetype blank, as Lambda will provide the metadata when pushing the events to Splunk
  - If this is your first HTTP Event Collector (HEC), make sure that HEC is enabled on **Global Settings**


## Option 2 - Using SNS + SQS
Template file: esp_sns_sqs_integration.json

The template produces the following resources:
- SNS Topic
- IAM role which allows ESP to assume role and push message to the SNS Topic
- SQS to receive ESP Alerts. [Splunk AWS Add-on](https://splunkbase.splunk.com/app/1876/) is utilized to pull the events from SQS to Splunk.

:warning: (This step is done manually because Cloudformation doesn't have the support for enabling RAW SQS message) Once the stack deployment is completed, open a new tab to SNS console and select the SNS created by the cloudformation template.
- Under subscriptions, check the subscription ID for SQS
- Select **Other Subscriptions options**, and **Edit Subscription Attributes**
- Select **Raw Message Delivery**
- Select **Set Subscription Attributes**


If you want to install [ESP Splunk App](https://splunkbase.splunk.com/app/3204/), dashboard will work with the following SQS input settings:
```
index: esp (app's default index)
interval: 60
sourcetype: **evidentio:alerts-sqs**
```