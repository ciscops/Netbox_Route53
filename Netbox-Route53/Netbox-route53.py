import datetime
import os
import sys
import logging
import pynetbox
import route53



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

    # Not sure if I need these yet:

    # self.nb_prefixes = self.nb.ipam.prefixes.all()
    # self.nb_ip_addresses = self.nb.ipam.ip_addresses.all()


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

    # I dont know if this works
    conn = route53.connect(
        aws_access_key_id=self.r53_id,
        aws_secret_access_key=self.r53_key,
    )

  # Not sure I need these functions
  # Might only need check_ip_addresses & maybe is_discovered

  # Prefix
  def check_prefixes(self, ip_address):
    for prefix in self.nb_prefixes:
        if prefix.status.value == 'active' and (ipaddress.ip_address(ip_address) in ipaddress.ip_network(
                prefix.prefix)):
            return prefix.prefix.split('/')[1]
    return None

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


#info to pass in
#all_prefixes = nb.ipam.prefixes.all()
#my_pfx = all_prefixes
#pfx = my_pfx.prefix
#pfx.hostmask
#pfx.ip + number


# Main updater - I think I'll be referencing this via lambda and passing in a group of ips to iterate through. This might change what needs to be passed in

   def check_record_exists(ip, sitename):
        R53_records = conn.get_zone(dns)
        for recordset in recordSets.get_records();
            if recordset.name == dns_record+"." & recordset.ip == dns_record:
                return True
   #add something here to update either one if one is true and the other isnt
   #I cant make much progress here without working with route53 records. The syntax and commands are
   #wrong but the idea is there

   def R53_create_record(ip, sitename):
        new_record, change_info = zone.create_a_record(name=sitename,values=ip)
        #Cant make much progress without testing this

   def integrate_records():
   #determine proper parameters to pass in for integrate_records. Is it "self"????
        all_prefixes = nb.ipam.prefixes.all()
        for record in all_prefixes:
            if check_record_exists(record.ip, record.site.name) == True:
                break
            else:
                R53_create_record(record.ip, record.site.name):



    if "NetBox_timeperiod" in os.environ:
            self.timespan = os.getenv("NetBox_timeperiod")
        else:
            self.timespan = 60 * 60 * 1

        self.netbox_time_format = '%Y-%m-%dT%XZ'


    def get_netbox_records(status, self)
        try:
            # Get list of records on network, filtering on self.timespan of last 14 days
            records = nb.ipam.ip_addresses.filter(status = active,
                                                  NetBox_timeperiod = self.timespan)











    #add error catches for the below functions
    #route53.exceptions.Route53Error
    #R53 function to update a records by passing in the prefix and ip (check both and update respectively)





    #R53 function to create a record by passing in the prefix and ip
    #def record_create(ip, prefix):
    #record_set.create_a_record(name, values, ttl=60, weight=None, region=None, set_identifier=None, alias_hosted_zone_id=None, alias_dns_name=None)
    #what record am I creating here? a/aaaa/cname/mx/ns/ptr/spf/srv/TXT/
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
