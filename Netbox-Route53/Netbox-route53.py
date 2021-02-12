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
            return ip, ip.dns_name



#side note, when eventually using this function, tie a variable to get_nb_records and pass it in as the parameter
   def check_and_update_r53_record(nb_ip, nb_dns):
       #IMPORTANT: Only update records you added. Make this the first thing you check before searching for route53 records
       #Use a tag like "is discovered" or "nbr53 marked"

       for record in r53 records: #fill this comand out
           if record.ip = nb_ip: #fill this command out
               if record.dns = nb_dns: #fill this command out
                   return True 
               else:
                   update_r53_record(nb_dns)
           elif record.dns = nb_dns: #fill out this command
               update_r53_record(nb_ip)
           else:
           return False


    def update_r53_record(ip, dns, *args, **kwargs):
        #for this command, experiment with it. I dont know the exact update commands and as long as I cant test it theres not much I can do
        #also test that it knows what is being passed in, if its either ip or dns and update accordingly. I don't want to make 2 functions
        #add a second check for a tag like "nbr53" to ensure this is the right one to edit. (This could be redundant and not needed however)

    def R53_create_record(ip, dns):
       new_record, change_info = zone.create_a_record(name=sitename,values=ip)
       #for this command, experiment with it. I dont know the exact update commands and as long as I cant test it theres not much I can do
       #Remember to add a tag when creating records that indicates this script created them

    def integrate_records(self):
        #iterate on nb ip addresses with get_nb_records (This will be tricky)
            #use check_and_update_r53_record with an if statement (Remember that the result from get_nb_records can be assigned to a
            #variable and passed into this function. Consider simplifying dns and ip to one single variable if you can figure out how
            #to seperate the two values)
                #use R53_create_record with the return value of get_nb_records. In this case its a complete true or false so just pass
                #in what gets returned

    #note, there will be alot of parameter passing. When this function progresses, find a way to keep it simple (ie: master variable)




    #    R53_records = conn.get_zone(dns)
    #    for recordset in recordSets.get_records();
    #        if recordset.name == dns_record+"." & recordset.ip == dns_record:
    #            return True
   #add something here to update either one if one is true and the other isnt
   #I cant make much progress here without working with route53 records. The syntax and commands are
   #wrong but the idea is there





    #Using a function for code simplicity to easily pass in netbox ip and prefix in the for loop later on
    #new_record, change_info = zone.create_a_record(name= prefix,values=ip,)


  # Code for R53 add / update records based on NB
  # Find out what is needed of the 3 functions defined
  # Above, and how they tie into comparing records in R53

  #comparing netbox to r53:
  #iterate through ips using netbox_ip
  #probably will use nb_ip_address (possibly could call the function and pass it in at the same time)
  #check if record_set . name is appropiate or if it should be record_set . ip (also find a way to print both r53 and nb ips and compare them manually first before automating)
  #find out what this code block below prints

  # Netbox stuff for getting prefixes
  pfx_search = nb.ipam.prefixes.all()

  for pfx in pfx_search:
  #pfx.prefix, pfx.status, pfx.ip,


netbox_ip = '(insert netbox ip here)'
for record_set in zone.record_sets:
    if record_set.name == netbox_ip:
        print(record_set)
        break

# Iterate through netbox ips on line 103
netbox_ip = '(insert netbox ip here)'
for record_set in zone.record_sets:
    if record_set.name == netbox_ip:
        print(record_set)
        break
    else:
        record_set.create_a_record(name, values, ttl=60, weight=None, region=None, set_identifier=None, alias_hosted_zone_id=None, alias_dns_name=None)

  # On line 109 figiure out what type of record to create with create_" "_record

  #saving a record (experiment with this) (this is if record exists but doesn't match)
record_set.values = ['insert record to be changed here']
record_set.save()

  #creating a record (pass in the ip and name from netbox)

new_record, change_info = zone.create_a_record(
name='test.some-domain.com.',
values=['8.8.8.8'],)

def R53_record_update(#all needed values to pass in):
    #(easier to just overwrite everything if the records dont match)
    record_set.values = ['insert record to be changed here']
    record_set.save()
    #Pass in record set (DONT FORGET)

 #for address in self.nb_ip_addresses:
     #iterate through all ip addresses. I believe you can pass in all ip's by this method and it works
     #check all of route53 records with each Ip iterated through (use in command)
      # if address in route53 records:
         #verify the rest of the values match
        #   if (needed values For netxbox record) == (needed values For route53):
        #       break
         #  else:
        # R53_record_update(pass In values From parameters):
       #else:
         #record_set.create_a_record(Needed values, See route53 python documentation):
