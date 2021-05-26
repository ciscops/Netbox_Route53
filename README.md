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

-Makefile
