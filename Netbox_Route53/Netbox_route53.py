from datetime import datetime, timedelta
import logging
import json
import os
import sys
import pynetbox
import boto3

# Either manually enter the necessary keys or set them as environment variables. The latter is recommended and examples are provided
# Export Netbox: url & token as env variables....Examples:
# export NETBOX_URL=https://example.net
# export NETBOX_TOKEN=guyg3r2fw8e7tgf2898366487n

# Export Route53: access_key_id, secret_access_key, HostZoneId....Examples:
# export ROUTE53_ID=KUYGDS783WSKI
# export ROUTE53_KEY=JHIU243YT9F8UHSUY983Y
# export ROUTE53_HOSTEDZONE_ID=EROTIJGOI438979800BW

#Note: these are made up keys and are not valid


class NetboxRoute53:
    def __init__(self):
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
        self.logging = logging.getLogger()

        # Initialize Netbox
        if "NETBOX_URL" in os.environ:
            self.nb_url = os.getenv("NETBOX_URL")
        else:
            logging.error("Environmnet variable NETBOX_URL must be set")
            sys.exit(1)

        if "NETBOX_TOKEN" in os.environ:
            self.nb_token = os.getenv("NETBOX_TOKEN")
        else:
            logging.error("Environmnet variable NETBOX_TOKEN must be set")
            sys.exit(1)

        self.nb = pynetbox.api(url=self.nb_url, token=self.nb_token)
        self.nb_ip_addresses = self.nb.ipam.ip_addresses.all()

        # Custom tag for marking records in route53 - this can be changed to any name
        self.r53_tag = "\"nbr53\""

        # Initialize Route53
        if "ROUTE53_ID" in os.environ:
            self.r53_id = os.getenv("ROUTE53_ID")
        else:
            logging.error("Environment variable ROUTE53_ID must be set")
            sys.exit(1)

        if "ROUTE53_KEY" in os.environ:
            self.r53_key = os.getenv("ROUTE53_KEY")
        else:
            logging.error("Environment variable ROUTE53_KEY must be set")
            sys.exit(1)

        # Gets the hosted zone id
        if "ROUTE53_HOSTEDZONE_ID" in os.environ:
            self.r53_zone_id = os.getenv("ROUTE53_HOSTEDZONE_ID")
        else:
            logging.error("Environment variable ROUTE53_HOSTEDZONE_ID must be set")
            sys.exit(1)

         # initiate connection to Route53 Via Boto3
        self.client = boto3.client(
             'route53',
             aws_access_key_id=self.r53_id,
             aws_secret_access_key=self.r53_key
        )

        # Get hosted_zone domain name for appending to record names
        Hosted_zone_response = self.client.get_hosted_zone(Id=self.r53_zone_id)
        HZ = json.dumps(Hosted_zone_response)
        HZ1 = json.loads(HZ)
        self.HZ_Name = HZ1['HostedZone']['Name']

        R53_get_response = self.client.list_resource_record_sets(HostedZoneId=self.r53_zone_id)
        self.R53_Record = json.dumps(R53_get_response)
        self.R53 = json.loads(self.R53_Record)

    def get_nb_records(self):
        timespan = datetime.today() - timedelta(hours=100, minutes=0)
        timespan.strftime('%Y-%m-%dT%XZ')
        ip_search = self.nb.ipam.ip_addresses.filter(within = self.nb_ip_addresses, last_updated__gte = timespan)
        return ip_search

    def discover_route53_records(self, dns, ip):
        nb_dns  = '''"''' + dns + '''"'''
        nb_ip = '''"''' + ip + '''"'''
        if nb_dns in self.R53_Record:
            self.check_route53_record(dns, ip)
        elif nb_ip in self.R53_Record:
            self.check_route53_record(dns, ip)
        else:
            return False

    def check_route53_record(self, dns, ip):
        tag = self.get_r53_record_tag(dns)
        v = self.R53_Record.count('''"Name"''')
        for n in range(0,v):
            R53_ip = self.R53['ResourceRecordSets'][n]['ResourceRecords'][0]['Value']
            R53_Record_name = self.R53['ResourceRecordSets'][n]['Name']
            if R53_Record_name == dns:
                if R53_ip == ip:
                    print("Record is a complete match")
                    return True
                else:
                    print("The ip passed in does not match the dns")
                    if tag:
                        print("Updating record")
                        self.update_r53_record(dns, ip)
                        return
                    else:
                        print("Record not tagged, cant update")
                        return
            elif ip == R53_ip:
                if self.get_r53_record_tag(R53_Record_name):
                    print("Record exists, but Dns is wrong, cleaning...")
                    self.delete_r53_record(R53_Record_name, ip)
                    self.create_r53_record(dns, ip)
                    print("Record cleaned")
                else:
                    print("Record not tagged, cant update")
                    return

    def get_r53_record_tag(self, dns):
        # For the tag check, this needs to be done with a dns query, it can't be done using the regular query
        R53_get_response = self.client.list_resource_record_sets(HostedZoneId=self.r53_zone_id, StartRecordName=dns, StartRecordType="TXT")
        R53_record = json.dumps(R53_get_response)
        R53 = json.loads(R53_record)
        if dns in self.R53_Record:
            R53_tag = R53['ResourceRecordSets'][0]['ResourceRecords'][0]['Value']
            R53_Record_name = R53['ResourceRecordSets'][0]['Name']
            R53_Record_type = R53['ResourceRecordSets'][0]['Type']
            if R53_Record_type == 'TXT':
                if R53_Record_name == dns:
                    if R53_tag == self.r53_tag:
                        return True

    def update_r53_record(self, dns, ip):
        response = self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
                'Comment': '',
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': dns,
                            'Type': 'A',
                            'TTL': 123,
                            'ResourceRecords': [
                                {
                                    'Value': ip,
                                },],}},]})

    def create_r53_record(self, dns, ip):
        response = self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
            'Changes': [
              {
                'Action': 'CREATE',
                'ResourceRecordSet' : {
                  'Name' : dns,
                  'Type' : 'A',
                  'TTL' : 123,
                  'ResourceRecords' : [{'Value': ip}]
                }
              },
              {
                'Action': 'CREATE',
                'ResourceRecordSet' : {
                  'Name' : dns,
                  'Type' : 'TXT',
                  'TTL' : 123,
                  'ResourceRecords' : [{'Value': self.r53_tag}]
                }}]})

    def delete_r53_record(self, dns, ip):
        response = self.client.change_resource_record_sets(
            HostedZoneId=self.r53_zone_id,
            ChangeBatch={
                'Comment': '',
                'Changes': [
                    {
                      'Action': 'DELETE',
                      'ResourceRecordSet' : {
                        'Name' : dns,
                        'Type' : 'A',
                        'TTL' : 123,
                        'ResourceRecords' : [{'Value': ip}]
                      }
                    },
                    {
                      'Action': 'DELETE',
                      'ResourceRecordSet' : {
                        'Name' : dns,
                        'Type' : 'TXT',
                        'TTL' : 123,
                        'ResourceRecords' : [{'Value': self.r53_tag}]
                      }}]})

    def clean_r53_records(self):
        v = self.R53_Record.count('''"Name"''')
        for n in range(0,v):
            R53_Record_type = self.R53['ResourceRecordSets'][n]['Type']
            R53_ip = self.R53['ResourceRecordSets'][n]['ResourceRecords'][0]['Value']
            R53_Record_name = self.R53['ResourceRecordSets'][n]['Name']
            value = "1"
            if self.get_r53_record_tag(R53_Record_name):
                if R53_Record_type == "A":
                    print("testing record: " + R53_Record_name)
                    for i in self.get_nb_records():
                        nb_dns = i.dns_name + "." + self.HZ_Name
                        ip = str(i)
                        sep = '/'
                        nb_ip = ip.split(sep, 2)[0]
                        if R53_Record_name == nb_dns and R53_ip == nb_ip:
                            print("record exists")
                            value = "1"
                            break
                        else:
                            value = "2"
            if value == "2":
                self.delete_r53_record(R53_Record_name, R53_ip)
                print("purge: " + R53_Record_name)

    def integrate_records(self):
        nb_records = self.get_nb_records()
        for i in nb_records:
            dns = i.dns_name + "." + self.HZ_Name
            ip = str(i)
            sep = '/'
            nb_ip = ip.split(sep, 2)[0]
            print("Checking record: " + dns + " " + ip)
            checkrecord = self.discover_route53_records(dns, nb_ip)
            if checkrecord:
                print("Record exists")
            else:
                print("Record doesn't exist, creating record...")
                self.create_r53_record(dns, nb_ip)
                print("Record created, continuing...")
