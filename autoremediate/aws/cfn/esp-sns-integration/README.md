# Evident ESP SNS Integration template

### Purpose

Amazon SNS is a notification service that tells Evident.io to send your alerts for desired
signatures to the teams that need them. This template creates the resources necessary to
configure an ESP SNS integration.

Amazon Simple Notification Service (Amazon SNS) is a fast, flexible, fully managed push
notification service that lets you send individual messages or to fan-out messages to large
numbers of recipients. 

---

### Usage

1. Download and save this template to a local file.
2. Login to your AWS account and navigate to the CloudFormation Dashboard.
3. From the **Select Template** page, select *Choose File* and this template from your local download location. Click *Open* in the pop-up window, then *Next*.
4. Enter a *Stack name* on the **Specify Details** page.
   1. Leave the *EspEvidentAccountId* parameter as is. 
   2. Enter a name for *SNSTopicDisplayName*, or leave the default.
   3. Click *Next*.
5. From the **Options** page, choose the options (if any) you want to enable, then click *Next*.
6. On the **Review** page, under **Capabilities**, check "I acknowledge that AWS CloudFormation might create IAM resources with custom names."
7. Click *Create* at the bottom of the **Review** page to launch the stack.

On the CloudFormation Dashboard, click on the **Events** tab to follow your Stacks progress.

8. Once the Stack has been created successfully, select the *Outputs* tab.

Here you will find the configuration information needed to complete a new Amazon SNS integration.

### ESP

1. Login to ESP
2. Follow the instructions to setup ESP SNS Integration: [ESP SNS Integration](https://esp.evident.io/control_panel/integrations/amazon_sns/)
3. 'Copy & Paste' the information from the **CloudFormation Stack Outputs** tab.
   1. Topic ARN
   2. Role ARN
   3. Replace the External ID with the one from the Outputs tab.
4. Select one or more External Accounts.
5. Choose one or more signatures to receive alerts from.
6. Save

