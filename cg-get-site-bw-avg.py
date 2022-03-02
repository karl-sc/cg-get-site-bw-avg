#!/usr/bin/env python
PROGRAM_NAME = "cg-get-site-bw-avg.py"
PROGRAM_DESCRIPTION = """
CloudGenix Get-Site-BW Daily Averages Script
---------------------------------------
Writes the past 7-days bandwidth average dailies and the 7-day average for each SPOKE site.
Output is placed in a CSV file

optional arguments:
  -h, --help            show this help message and exit
  --token "MYTOKEN", -t "MYTOKEN"
                        specify an authtoken to use for CloudGenix
                        authentication
  --authtokenfile "MYTOKENFILE.TXT", -f "MYTOKENFILE.TXT"
                        a file containing the authtoken
  --csvfile csvfile, -c csvfile
                        the CSV Filename to write the BW averages to

"""

####Library Imports
from cloudgenix import API, jd
import os
import sys
import argparse
from csv import reader


def parse_arguments():
    CLIARGS = {}
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=PROGRAM_DESCRIPTION
            )
    parser.add_argument('--token', '-t', metavar='"MYTOKEN"', type=str, 
                    help='specify an authtoken to use for CloudGenix authentication')
    parser.add_argument('--authtokenfile', '-f', metavar='"MYTOKENFILE.TXT"', type=str, 
                    help='a file containing the authtoken')
    parser.add_argument('--csvfile', '-c', metavar='csvfile', type=str, 
                    help='the CSV Filename to write the BW averages to', required=True)
    args = parser.parse_args()
    CLIARGS.update(vars(args))
    return CLIARGS

def authenticate(CLIARGS):
    print("AUTHENTICATING...")
    user_email = None
    user_password = None
    
    sdk = API()    
    ##First attempt to use an AuthTOKEN if defined
    if CLIARGS['token']:                    #Check if AuthToken is in the CLI ARG
        CLOUDGENIX_AUTH_TOKEN = CLIARGS['token']
        print("    ","Authenticating using Auth-Token in from CLI ARGS")
    elif CLIARGS['authtokenfile']:          #Next: Check if an AuthToken file is used
        tokenfile = open(CLIARGS['authtokenfile'])
        CLOUDGENIX_AUTH_TOKEN = tokenfile.read().strip()
        print("    ","Authenticating using Auth-token from file",CLIARGS['authtokenfile'])
    elif "X_AUTH_TOKEN" in os.environ:              #Next: Check if an AuthToken is defined in the OS as X_AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
        print("    ","Authenticating using environment variable X_AUTH_TOKEN")
    elif "AUTH_TOKEN" in os.environ:                #Next: Check if an AuthToken is defined in the OS as AUTH_TOKEN
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
        print("    ","Authenticating using environment variable AUTH_TOKEN")
    else:                                           #Next: If we are not using an AUTH TOKEN, set it to NULL        
        CLOUDGENIX_AUTH_TOKEN = None
        print("    ","Authenticating using interactive login")
    ##ATTEMPT AUTHENTICATION
    if CLOUDGENIX_AUTH_TOKEN:
        sdk.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if sdk.tenant_id is None:
            print("    ","ERROR: AUTH_TOKEN login failure, please check token.")
            sys.exit()
    else:
        while sdk.tenant_id is None:
            sdk.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not sdk.tenant_id:
                user_email = None
                user_password = None            
    print("    ","SUCCESS: Authentication Complete")
    return sdk

def logout(sdk):
    print("Logging out")
    sdk.get.logout()


##########MAIN FUNCTION#############
def go(sdk, CLIARGS):
    ####CODE GOES BELOW HERE#########
    csvfilename = CLIARGS['csvfile']
    resp = sdk.get.tenants()
    if resp.cgx_status:
        tenant_name = resp.cgx_content.get("name", None)
        print("======== TENANT NAME",tenant_name,"========")
    else:
        logout()
        print("ERROR: API Call failure when enumerating TENANT Name! Exiting!")
        print(resp.cgx_status)
        sys.exit((vars(resp)))

    result = sdk.get.sites()
    if not result.cgx_status:
        sys.exit("Error Getting Site list")
    site_list = result.cgx_content.get("items")

    parsed_sites = []
    for site in site_list:
        if site['element_cluster_role'] == "SPOKE":
            parsed_sites.append([site['name'], site['id']])

    csv_out_array = [['SiteName', 'SiteID', '24Hr-Today', '24Hr-Yesterday',  '24Hr-3-days-ago', '24Hr-4-days-ago', '24Hr-5-days-ago', '24Hr-6-days-ago', '24Hr-7-days-ago',  '7-Day-AVG' ]]
    for site_data in parsed_sites:
        site_name = site_data[0]
        site_id = site_data[1]
        sum = 0
        csv_row = []
        csv_row.append(site_name) #1
        csv_row.append(site_id) #2
        for days_back in range(0,7): #7 days worth of data
            (start_time, end_time) = cgx_generate_timestamps_days(days_interval=1, offset_days=days_back)
            day_bw = cgx_get_bw_consumption(sdk, start_time, end_time, site_id=site_id)  
            csv_row.append( day_bw ) # 3-10
            sum += day_bw
        sum = ( sum / 7 ) #7-day average
        csv_row.append( round(sum,2) ) # 11
        csv_out_array.append(csv_row) ## add the sites row
    
    result = False
    result = write_2d_list_to_csv(csvfilename, csv_out_array)
    if result:
        print("Wrote CSV File",csvfilename,"Successfully")
    else:
        print("Failure Writing CSV File")
    ####CODE GOES ABOVE HERE#########
  


#/----------------------
#| cgx_generate_timestamps_days - Generates CGX start and end Timestamps used in events, alarms, reporting for specified interval in days (default 1 day or 24 hours)
def cgx_generate_timestamps_days(days_interval=1, offset_days=0):
    from datetime import timedelta
    from datetime import datetime
    now = (datetime.utcnow() - timedelta(days=(offset_days)))
    end_time = now.isoformat()
    start_time = (now - timedelta(days=(days_interval))).isoformat() 
    return (str(start_time)+"Z", str(end_time)+"Z") ## return (start_time, end_time) I.E. call with "(start_time, end_time) = cgx_generate_timestamps(days_interval=1) for the last 24 hours"
#\----------------------


#/----------------------
#| validate_2d_array - Validates an array is 2-dimensional for use in CSV Export
def validate_2d_array(test_list):
    import numpy as np
    np_list = np.array(test_list)
    if len(np_list.shape) == 2:
        return True
    return False
#\----------------------


#/----------------------
#| write_2d_list_to_csv - Writes a 2-Dimensional list to a CSV file
def write_2d_list_to_csv(csv_file, list_2d, write_mode="w"):
    import csv
    try:
        file = open(csv_file, write_mode)
        with file:    
            write = csv.writer(file)
            write.writerows(list_2d)
            return True
        return False
    except:
        return False

#\----------------------

#/----------------------
#| cgx_average_series - takes a metrics series structure (input['metrics']['series']['data']['datapoints'][**list**]['value']) and averages it to the decimal places (default:2)
#|                  A typical call would look like: 
#|                      metrics = cgx_get_bw_consumption(sdk,start,end) ## Calls sdk.post.monitor_metrics and returns Metrics with Series in them
#|                      for series in metrics.get("metrics",[{}])[0].get("series",[]):
#|                          average = cgx_average_series(series)
def cgx_average_series(metrics_series_structure, decimal_places=2):
    count = 0
    sum = 0
    for datapoints in metrics_series_structure.get("data",[{}])[0].get("datapoints",[{}]):
        if (datapoints.get("value",None) is not None):
            count += 1
            sum += datapoints.get("value",0)
    if count != 0:
        if decimal_places == 0:
            return round((sum/count))
        return round((sum/count),decimal_places)
    return 0
#\----------------------

#/----------------------
#| cgx_get_bw_consumption - Gets bandwidth consumption average for a give time period. If no site_id is given, Aggregate BW consumption for the tenant is provided.
def cgx_get_bw_consumption(sdk, start_time, end_time, site_id=None):
    true = True
    false = False
    post_request = {"start_time":start_time, "end_time":end_time, "interval":"5min","metrics":[{"name":"BandwidthUsage","statistics":["average"],"unit":"Mbps"}],"view":{},"filter":{"site":[]}}
    if site_id: post_request['filter']['site'].append(str(site_id))
    result = sdk.post.monitor_metrics(post_request)
    metrics = result.cgx_content
    series = metrics.get("metrics",[{}])[0].get("series",[{}])[0]
    return(cgx_average_series(series))
#\----------------------


if __name__ == "__main__":
    ###Get the CLI Arguments
    CLIARGS = parse_arguments()
    
    ###Authenticate
    SDK = authenticate(CLIARGS)
    
    ###Run Code
    go(SDK, CLIARGS)

    ###Exit Program
    logout(SDK)
