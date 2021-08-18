# Netbox-Route53-Integration

Lambda or Terminal run script, using Netbox as a source of truth to integrate ip/dns pairs into Route53 via webhook or on a schedule basis.

## Requirements  
* Boto3 1.17.6
* Netbox 6.1.3
* Python 3.8

## Description

Netbox-Route53-Integration can be run either on terminal/cmd, or in AWS Lambda.
The script runs in lambda using apigateway and Cloudwatch respectively, to
maintain record synchronization.

The webhook function reacts on an creation/update/deletion of a record in netbox
and changes the record in route53 accordingly, using a combination of netbox
webhooks and apigateway to communicate to the AWS function.

Apigateway does a periodic sync between all current records in netbox,
verifying all records match. It will then remove any route53 records that don't
have a matching set in netbox. All records created in route53 are tagged with a
user-specified tag which prevents the script from changing or deleting existing
records without this tag.

Netbox is seen as the source of truth by this script, and will only react to what
is listed in netbox. There are no changes made to the records inside of netbox.


### Aws Function Setup   
To prepare the framework inside AWS LAMBDA for uploading the script via Makefile commands

-Create a lambda function, appropriately named
(Use Python version 3.8)  
* [Aws docs Functions](https://docs.aws.amazon.com/lambda/latest/dg/getting-started-create-function.html)


-Aws Cloudwatch Trigger Setup  
(Start from step 2, set timer to run every 30 minutes)
* [Aws docs Cloudwatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/RunLambdaSchedule.html)

To store the timespan within cloudwatch timer for multiple timer use, under targets, constant(json text) paste
the following:  {"Timespan": "1" }   (note, any other cloudwatch timers will be set up the same but with different time spans)

If there is no cloudwatch timespan set, or is set incorrectly, the script will use the environment variable "TIMESPAN"

-Aws API Gateway Trigger Setup  
(For the Netbox setup below, you will need the AWS API gateway Arn from creating an api gateway trigger)
* [Aws docs Apigateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started.html)


### Netbox Webhook Setup
To enable Netbox webhooks:
* [Netbox docs Webhooks](https://netbox.readthedocs.io/en/stable/additional-features/webhooks/)


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


### Makefile
To push script to lamdba, use Makefile commands

Rename LAMBDA_FUNCTION_NAME inside the makefile to match the name of the  Aws Lambda function

(Terminal/Cmd commands to port script to aws)

-Specify Aws account details
```bash
aws configure    
aws sts get-caller-identity
```

-Compile Script and upload to both functions

```bash
make lambda-layer
make lambda-upload-webhook
make lambda-upload-auto
```    
