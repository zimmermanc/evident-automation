ESP Alerts Export to S3 through Kinesis Firehose
-----

The cloudformation stack generates the following resources:
- SNS to receive ESP alerts
- Lambda to push the alert to Kinesis Firehose
- Kinesis Firehose stream
- IAM roles with enough permissions to glue the stack together.

Step-by-step instructions:
1. Zip evident.py and upload it to an S3 bucket. The S3 bucket should be in the same region as the cloudformation stack
2. Launch the cloudformation stack using EvidentKinesisFirehose.json. 
    - TargetS3Bucket: Exported alerts will go to this bucket. THis should be an existing S3 bucket.
    - SourceCodeBucket: The S3 bucket from step #1
    - SourceCodeKeyPath: THe path of the zipped package from step #1.

evident.py script by default pushes the raw ESP alert message. If you want to change the format, you can modify 
```
#############################################
# Inputs: Takes JSON object
# Action: Format JSON object
# Returns: JSON object
#
#############################################
def format_alert(alert):
    return alert
```