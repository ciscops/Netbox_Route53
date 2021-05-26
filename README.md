# Netbox-Route53-Integration

Lambda or Terminal run script, using Netbox as a source of truth to integrate ip/dns pairs into Route53 on a schedule basis.

-Requirements
Boto3
Netbox
Python

-Description

Netbox-Route53-Integration can be run either on terminal/cmd, or in AWS Lambda. Both methods use the single designated Lambda
script, Lambda_function.py, as the main control for the integration script, Netbox_Route53.py. This lambda script, which can
be run in both terminal/cmd and lambda, initially runs netbox_r53.integrate_records(), to import any records which have been
modified in the timespan specified by the user in the environment variables. This function will check all records in that
timespan, and verify if a) it already exists, or b) it doesn't, either leaving the record alone, or creating it in Route53
respectively. Lambda_function.py then runs netbox_r53.clean_r53_records(), which checks if all records in Route53 match those
in Netbox, purging any that do not. Additionally, the user will be required to specify a custom tag as an env var which will accompany
each Route53 record created by this script, ensuring only those records can be updated or deleted.


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
