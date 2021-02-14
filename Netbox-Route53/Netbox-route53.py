from datetime import datetime, timedelta
import os
import sys
import logging
import pynetbox
import route53
import boto3


class NetboxRoute53:
    def __init_(self):

        # Initialize logging
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

        client = boto3.client(
            's3',
            aws_access_key_id=self.r53_id,,
            aws_secret_access_key=self.r53_key,
            aws_session_token=self.r53_token
        )

  # Ip - address
    def check_ip_addresses(self, ip_address):
        for nb_ip_address in self.nb_ip_addresses:
            if ip_address in nb_ip_address.address:
                return nb_ip_address
        return None

  # discovered tag
    def is_discovered(self, nb_ip_address):
        for tag in nb_ip_address.tags:
            if tag.name == self.discovered_tag:
                return True
        return False

    def get_nb_records(self):
    timespan = datetime.today() - timedelta(hours=24, minutes=0)
    timespan.strftime('%Y-%m-%dT%XZ')
    ip_search = nb.ipam.ip_addresses.filter(within = self.nb_ip_addresses, last_updated__gte = timespan)
        for ip in ip_search:
            return ip, ip.dns_name #might need to make this into a single variable. Keep it as is for now

    #Todo:
    #Test how this function works with the others, including passing in the variables properly
    #Make sure the formats for the ip and dns are correct between netbox and Route53
    #Figure out the variable returning

#side note, when eventually using this function, tie a variable to get_nb_records and pass it in as the parameter
   def check_and_update_r53_record(nb_ip, nb_dns):
       #IMPORTANT: Only update records you added. Make this the first thing you check before searching for route53 records
       #Use a tag like "is discovered" or "nbr53 marked"


       #IMPORTANT: Possibly sift through record sets first based on the tag nbr53
       #this can be complicated but test querying the db based on the tag

       # list-tags-for-resource
       #--resource-type <value>
       #--resource-id <value>

       #Something like query a record, then query its tag, if the tag matches nbr53 continue with updating
       #If this doesnt work, maybe use the built-in healthcheck tag and assign that as nbr53 and query it

       #Use ListResourceRecordSets to get the ips and dns names. This will require testing

       for record in r53 records: #fill this comand out
           if record.ip = nb_ip: #fill this command out
               if record.dns = nb_dns: #fill this command out
                   return True
               else:
                   update_r53_record(ip = nb_ip, dns = nb_dns, update = "dns")
           elif record.dns = nb_dns: #fill out this command
               update_r53_record(ip = nb_ip, dns = nb_dns, update = "ip")
           else:
           return False
           #Play around with the update command. Hard to predict what it will do
           #and how to find and properly update a record. You probably need to specify
           #one or the other so chances are there may be more to fix with update_r53_record

         #Todo:
         #Fill out commands where needed.
         #Figure out how to pull ip and dns for a single record set
         #Test This ^
         #Test the logic for this command
         #Make sure variables are passed in properly for #update_r53_record
         #Test this ^
         #Make sure the update variable is passed in properly
         #Test this with #integrate_records


    def update_r53_record(ip, dns, update):
        #So for the sake of simplicty, just overwrite the existing ip or dns name, Since one will be correct and the other wrong,
        #It saves the hassle of having to figure out which one needs updating. A little tricky logically but it should work

        #this actually may take testing. From aws docs it seems it changes based on 'name'. Expirment with this

        #Before upserting, making sure the record has the right tags
        #Also figure out the update order and the priority of what gets updated
        #Based on whats passed in. It might make sense to pass in a third variable in them
        #check_and_update_r53_record part that specifies what gets updated and pass in both
        #this way makes it easier to create a for loop

        # IMPORTANT

        #Todo:
        #Figure out the nbr53 tag part
        #Figure out how to update one or the other. You can't just update a record without specifying which record it is
        #you are updating
        #Test

        order = update
        if order = "ip":
            response = client.change_resource_record_sets(
            HostedZoneId='string', #pass this in manually
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': dns,
                            'Type': 'A',
                            'ResourceRecords': [
                                {
                                'Value': ip,
                                },
                            ],},},],},)
        elif order = "dns":
            response = client.change_resource_record_sets(
            HostedZoneId='string', #pass this in manually
            ChangeBatch={
                'Changes': [
                 {
                     'Action': 'UPSERT',
                     'ResourceRecordSet': {
                         'Name': dns,
                         'Type': 'A',
                         'ResourceRecords': [
                             {
                             'Value': ip,
                             },
                         ],},},],},)


    def R53_create_record(ip, dns):
        response = client.change_resource_record_sets(
        HostedZoneId='string', #pass this in
        ChangeBatch={
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': dns,
                        'Type': 'A',
                        'ResourceRecords': [
                            {
                            'Value': ip,
                            },
                        'ResourceTagSet': {
                            'Tags': [
                                {
                                    'Key': 'Tagged',
                                    'Value': 'nbr53'
                                },]}
                        ],},},],},)

                        #Todo:
                        #Test that this properly creates a record
                        #Test that the tag is properly added
                        #Test that for any ip or dns, it will create the right record


       #Remember to add a tag when creating records that indicates this script created them

       #Name (string) -- [REQUIRED]
       #For ChangeResourceRecordSets requests, the name of the record that you want to create, update, or delete.
       #For ListResourceRecordSets responses, the name of a record in the specified hosted zone.

       #ChangeResourceRecordSets Only
       #Enter a fully qualified domain name, for example, www.example.com .
       #You can optionally include a trailing dot. If you omit the trailing dot,
       #Amazon Route 53 assumes that the domain name that you specify is fully qualified.
       #This means that Route 53 treats www.example.com (without a trailing dot) and www.example.com. (with a trailing dot) as identical.


    def integrate_records(self):
        #iterate on nb ip addresses with get_nb_records (This will be tricky)
            #use check_and_update_r53_record with an if statement (Remember that the result from get_nb_records can be assigned to a
            #variable and passed into this function. Consider simplifying dns and ip to one single variable if you can figure out how
            #to seperate the two values)
                #use R53_create_record with the return value of get_nb_records. In this case its a complete true or false so just pass
                #in what gets returned

    #note, there will be alot of parameter passing. When this function progresses, find a way to keep it simple (ie: master variable)


    #Todo:
    #Fill this command out once all the other commands work flawlessly
    #Test this command with foo data
    #Test this command against netbox data
