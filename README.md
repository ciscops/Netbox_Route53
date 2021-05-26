# Netbox-Route53-Integration

Lambda or Terminal run script, using Netbox as a source of truth to integrate ip/dns pairs into Route53 via webhook or on a schedule basis.

-Requirements
Boto3
Netbox
Python

-Description

Netbox-Route53-Integration can be run either on terminal/cmd, or in AWS Lambda.
The script runs in lambda either via webhook or on a timer, using apigateway or
Cloudwatch respectively. There is a separate lambda script for each of the two
functions (webhook and timer based) can run simultaneously in the same Aws
account.

The script file Netbox_route53.py, is identical between the two functions
and the difference is in the lambda_fuction_(auto or webhook).py files, which
specify which parts of the script will run.

The webhook function reacts on an creation/update/deletion of a record in netbox
and changes the record in route53 accordingly, using a combination of netbox
webhooks and apigateway to communicate to the AWS function.

The automatic version does a periodic sync between all current records in netbox,
verifying all records match. It will then remove any route53 records that don't
have a matching set in netbox. All records created in route53 are tagged with a
user-specified tag which prevents the script from changing or deleting existing
records without this tag.

Netbox is seen as the source of truth by this script, and will only react to what
is listed in netbox. There is not changes made to the records inside of netbox.


-Aws Function Setup   
To prepare the framework inside AWS LAMBDA for uploading the script via Makefile commands

Create two lambda functions, one titled for webhook, and one titled for auto timer based running  
Use Python version 3.8:   
https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html

-Aws Cloudwatch Trigger Setup
(Start from step 2)
https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html

-Aws API Gateway Trigger Setup  
(For the Netbox setup below, you will need the AWS API gateway Arn from creating an api gateway trigger)
https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started.html

-Netbox Webhook Setup
To enable Netbox webhooks

  Netbox>Admin>Webhooks>Add Webhook

  Name: ()
  Object types: (IP addess, prefix)  
  Enabled: (checked)  
  Type Create: (checked)  
  Type Update: (checked)  
  Type Delete: (checked)  
  URL: (AWS API gateway arn) < (See Api gateway trigger setup)  
  HTTP method: (POST)
  HTTP content type: (application/json)


-Makefile
  To push script to lamdba, use Makefile commands

  (Edit names to match the fuction names created in AWS LAMBDA, do this within your local makefile)
  LAMBDA_WEBHOOK_FUNCTION=" " (For the Webhook function)  
  LAMBDA_AUTO_FUNCTION=" "    (For the timer based function)  

  (Terminal/Cmd commands)   
  -aws configure (Input aws account access key, secret access key, region, and output format)    
  -aws sts get-caller-identity (Verify details)

  -make lambda-layer (Complies script code)
  -make lambda-upload-webhook (Uploads script for the webhook function to aws)  
  -make lambda-upload-auto    (Uploads script for the schedule bases function to aws)
