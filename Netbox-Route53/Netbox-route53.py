from datetime import datetime, timedelta
import boto3
import logging
import json
import os
import pynetbox
import sys
import route53



class NetboxRoute53:
    def __init_(self):

        # Initialize logging
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
        self.logging = logging.getLogger()
        # Review the need for this

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

        #initiate connection to netbox
        self.nb = pynetbox.api(url=self.nb_url, token=self.nb_token)
        self.nb_ip_addresses = self.nb.ipam.ip_addresses.all()
        #This is in a function. Figure out how to call it from another function

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

        if "ROUTE53_TOKEN" in os.environ:
            self.r53_token = os.getenv("ROUTE53_TOKEN")
        else:
            logging.error("Environment variable ROUTE53_TOKEN must be set")
            sys.exit(1)

        # Gets the hosted zone id
        if "ROUTE53_HOSTEDZONE_ID" in os.environ:
            self.r53_zone_id = os.getenv("ROUTE53_HOSTEDZONE_ID")
        else:
            logging.error("Environment variable ROUTE53_HOSTEDZONE_ID must be set")
            sys.exit(1)

        # initiate connection to Route53 Via Boto3
        client = boto3.client(
            'route53',
            aws_access_key_id=self.r53_id,
            aws_secret_access_key=self.r53_key
        )

        Hosted_zone_response = client.get_hosted_zone(Id=self.r53_zone_id)
        HZ = json.dumps(Hosted_zone_response)
        HZ1 = json.loads(HZ)
        HZ_Name = HZ1['HostedZone']['Name']
        # Gets the hosted zone name from route53. This is to use to match dns names with the hosted zone appended
        # It can easily be removed

        #Find out how to call HZ_Name from other functions

    # Get Netbox records based on a timespan. Need to add functionallity to vary timespans, such as
    # 24hr x 3 then a 48hr check, but not inside of this function
    def get_nb_records(self):
        timespan = datetime.today() - timedelta(hours=24, minutes=0)
        timespan.strftime('%Y-%m-%dT%XZ')
        ip_search = nb.ipam.ip_addresses.filter(within = self.nb_ip_addresses, last_updated__gte = timespan)
        return ip_search

    # Checks if a netbox record exists in route53, updates record accordingly and returns relevant information
    # To record integrator
    def discover_route53_records(dns, ip):
        R53_get_response = client.list_resource_record_sets(HostedZoneId='')
        R53_record = json.dumps(R53_get_response)
        R53 = json.loads(R53_record)
        nb_dns  = '''"''' + dns + '''"'''
        nb_ip = '''"''' + ip + '''"'''
        print("Checking record" + " " + dns + " " + ip)
        if nb_dns in R53_record:
            check_route53_record(dns, ip)
        elif nb_ip in R53_record:
            check_route53_record(dns, ip)
        else:
            return False

    def check_route53_record(dns, ip):
        R53_get_response = client.list_resource_record_sets(HostedZoneId='')
        R53_record = json.dumps(R53_get_response)
        R53 = json.loads(R53_record)
        tag = get_r53_record_tag(dns)
        try:
            n = 0
            while n < 101:
                R53_Record_type = R53['ResourceRecordSets'][n]['Type']
                R53_ip = R53['ResourceRecordSets'][n]['ResourceRecords'][0]['Value']
                R53_Record_name = R53['ResourceRecordSets'][n]['Name']
                #print("Checking if " + ip + " Matches " + R53_ip)
                if R53_Record_name == dns:
                    if R53_ip == ip:
                        print("Record is a complete match")
                        return True
                    else:
                        print("The ip passed in does not match the dns")
                        if tag == True:
                            print("Updating record")
                            update_r53_record(dns, ip)
                            return "Retryrecord"
                        else:
                            print("Record not tagged, cant update")
                            return
                    n += 1
                elif ip == R53_ip:
                    print("catch")
                    if get_r53_record_tag(R53_Record_name) == True:
                        print("Record exists, but Dns is wrong, cleaning...")
                        delete_r53_record(R53_Record_name, ip, "A")
                        delete_r53_record(R53_Record_name, "\"nbr53\"", "TXT")
                        create_r53_record(dns, ip)
                        print("Record cleaned")
                    else:
                        print("Record not tagged, cant update")
                        return
                        n += 1
                else:
                    n += 1
        except:
            pass


    # Checks if a record that needs to be updated, is tagged with "nbr53"
    def get_r53_record_tag(dns):
        R53_get_response = client.list_resource_record_sets(HostedZoneId='', StartRecordName=dns, StartRecordType="TXT")
        R53_record = json.dumps(R53_get_response)
        R53 = json.loads(R53_record)
        if dns in R53_record:
            R53_tag = R53['ResourceRecordSets'][0]['ResourceRecords'][0]['Value']
            R53_Record_name = R53['ResourceRecordSets'][0]['Name']
            R53_Record_type = R53['ResourceRecordSets'][0]['Type']
            if R53_Record_type == 'TXT':
                if R53_Record_name == dns:
                    if R53_tag == "\"nbr53\"":
                        return True

    # Updates a record's ip if it is incorrect
    def update_r53_record(dns, ip):
    response = client.change_resource_record_sets(
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

    # Creates an A record based on NB ip and dns, and an accompanying TXT record for tagging
    def create_r53_record(dns, ip):
    response = client.change_resource_record_sets(
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
              'ResourceRecords' : [{'Value': "\"nbr53\""}]
            }}]})

    # Iterates through Netbox records and checks if they exist in route53, if they don't they are created
    # and if the ip assigned doesn't match Netbox's ip, it updates it only if it is tagged as "nbr53"
    def integrate_records():
        for i in get_nb_records():
            dns = i.dns_name + "." + HZ_Name
            ip = str(i)
            sep = '/'
            nb_ip = ip.split(sep, 2)[0]
            checkrecord = discover_route53_records(dns, nb_ip)

            #The addition of HZ_Name has to do with hosted zones. This functionallity is easily removable
            if checkrecord == True:
                print("Record exists")
            elif checkrecord == "NotArecord":
                print("Not A valid record")
                #This is here just incase it catches a non A record that passed in
            elif checkrecord == "Retryrecord":
                print("Retrying record: ")
                checkrecord = discover_route53_records(dns, nb_ip)
                if checkrecord == True:
                    print("ip set properly, continuing...")
            elif checkrecord == False:
                print("Record doesn't exist, creating record...")
                create_r53_record(dns, nb_ip)
                print("Record created, continuing...")
            elif checkrecord == "CleanRecord":
                print("Record cleaned continuing...")
                checkrecord = discover_route53_records(dns, nb_ip)
                if checkrecord == True:
                    print("Record cleaned continuing...")
