import datetime
from Netbox_Route53_integration import NetboxRoute53

if __name__ == '__main__':
    start_time = datetime.datetime.now()
    netbox_r53 = MerakiNetbox()
    netbox_r53.integrate_records()
    netbox_r53.clean_r53_records()
    end_time = datetime.datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')
