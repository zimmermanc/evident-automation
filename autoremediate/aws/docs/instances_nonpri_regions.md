### Instances Found In Non-Priority Regions Auto-Remediate Walkthrough

This document walks through the steps to create an ESP custom signature, configure ESP SNS integration, and send alerts as events to Lambda for remediation.  The auto-remediation script used in this walkthrough identifies running/stopped instances in non-priority regions and attempts to; 1.) Create a backup image (AMI) of the EC2 instance and 2.) Terminate the instance.


#### Create ESP Custom Signature

1. Login to ESP
2. On the top pane, select Control Panel, then Custom Signatures from the left-side column
3. Create a New signature
    * Name: **Instances in Non Priority Regions** 
    * Risk Level: **Low**
    * Identifier: **AWS::EC2::???**
    * Description: "Identifies running/stopped instances in non-priority regions and attempts to; 1.) Create a backup image (AMI) of the EC2 instance and 2.) Terminate the instance."
    * Select a Team (or Teams) and Submit
    * Copy & paste the code from the following link: https://github.com/EvidentSecurity/custom_signatures/blob/master/AWS_EC2%20-%20instances_nonpri_regions.rb
4. Save your signature, but don't activate it just yet


#### ESP SNS Integration

1. Follow the instructions to setup ESP SNS Integration: https://esp.evident.io/control_panel/integrations/amazon_sns/new
    * SNS Topic Name: **instances-non-pri-regions-topic**
    * Teams: Select the same team(s) as above in the Create Custom Signature step
    * Alert Types: Check **Fail** (Uncheck all others)
    * Signatures: Select **Amazon Low Risk Signatures** and choose the custom signature we just created; *Instances in Non Priority Regions*


#### Create IAM Policy and Role for Lambda

###### Lambda IAM Policy

1. From the AWS Console, IAM Dashboard, under Policies, select Create Policy
2. Select Create Your Own Policy
3. Name the policy: **instances-non-pri-regions-lambda**
4. In the Policy Document, copy & paste the policy from the following link: https://github.com/EvidentSecurity/automation/blob/master/autoremediate/aws/policies/AWS_EC2_instances_nonpri_regions_policy.json
5. Select Create Policy

###### Lambda IAM Role

1. From the IAM Dashboard, under Roles, select Create new role
2. Select the AWS Lambda role type 
3. Attach two policies:
    * Check the policy we created above; *instances-non-pri-regions-lambda*
    * Check the AWS managed policy; *AWSLambdaBasicExecutionRole*
4. Select Next Step 
5. Name the role: **instances-non-pri-regions-lambda** and select Create role


#### Create Auto-Remediation Lambda Function

1. From the AWS Lambda Dashboard, select Create a Lambda function
2. Select the blueprint; *sns-message-python*
3. From the SNS topic drop-down menu, select the SNS topic we created in the integration step; *instances-non-pri-regions-topic*
4. Check Enable trigger and select Next
5. Name the function and give it a description (if desired)
6. In the Lambda function code window, copy & paste the following auto-remediation script: https://github.com/EvidentSecurity/automation/blob/master/autoremediate/aws/lambda/AWS_EC2_instances_nonpri_regions_remediate.py
7. Under the Existing role drop-down menu, choose the Lambda Role we created above; *instances-non-pri-regions-lambda*
8. Toggle Advancing settings and enter the following:
    * Set the timeout value to **5 minutes** (the max)
    * No VPC access is required
9. Select Next and Create function


#### Activate ESP Custom Signature

1. Login to ESP
2. On the top pane, select Control Panel, then Custom Signatures from the left-side column
3. Locate the *Instances in Non Priority Regions* signature, select View and Activate


Check CloudWatch Logs for auto-remediation output.
