# cg-get-site-bw-avg
Gets 7 days of site bw averages for all sites

## CloudGenix Get-Site-BW Daily Averages Script ##
```
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

```
