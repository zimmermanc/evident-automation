from __future__ import print_function
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from hashlib import sha1

import uuid
import pycurl
import json
import md5
import base64
import cStringIO
import hmac
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

#=== Description ===
# Send an email with weekly stats.  The email includes 3 main sections: 1) total risks across all accounts your
# user can access, 2) risks by teams, 3) top 5 control checks with most risks
# Note: risks are failed alerts (does not include warnings)
#
# Instructions:
# 1. Enter your ESP API Public Key and Secret Key
# 2. Create a Gmail account
# 3. (Recommended) Enable 2FA and generate an app password
# 4. Enter your Gmail account and password
# 5. Enter the list of emails you want to send report to
# 6. (Recommended) Create a cron job to run this script once a week
#
#=== End Description ===

#=== Configuration ===

# ESP API Access Key Credentials
public = <public key>
secret = <secret key>

# Email
emails = ['admin@somecompany.com']
gmail_user = <gmail user> # e.g my_account@gmail.com
gmail_password = <password> # recommend using app password

#=== End Configuration ===

# Helper method - process API requests
def call_api(action, ev_create_url, data, count = 0):
    url = ev_create_url.split('evident.io')[1]
    
    # Create md5 hash of body
    m = md5.new()
    m.update(data.encode('utf-8'))
    data_hash = base64.b64encode(m.digest())
    
    # Find Time
    now = datetime.now()
    stamp = mktime(now.timetuple())
    
    # Create Authorization Header
    canonical = '%s,application/vnd.api+json,%s,%s,%s' % (action, data_hash, url, format_date_time(stamp))
    
    hashed = hmac.new(secret, canonical, sha1)
    auth = hashed.digest().encode("base64").rstrip('\n')
    
    # Create Curl request
    buf = cStringIO.StringIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, str(ev_create_url))
    c.setopt(pycurl.HTTPHEADER, [
        'Date: %s' % format_date_time(stamp),
        'Content-MD5: %s' % data_hash,
        'Content-Type: application/vnd.api+json', 
        'Accept: application/vnd.api+json',
        'Authorization: APIAuth %s:%s' % (public, auth)])
    c.setopt(c.WRITEFUNCTION, buf.write)
    
    if action == 'POST':
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, data)
    elif action == 'PATCH':
        c.setopt(c.CUSTOMREQUEST, 'PATCH')
        c.setopt(pycurl.POSTFIELDS, data)
    elif action == 'DELETE':
        c.setopt(c.CUSTOMREQUEST, 'DELETE')
        c.setopt(pycurl.POSTFIELDS, data)
    c.perform()
    ev_response = buf.getvalue()
    buf.close()
    c.close()
    ev_response_json = json.loads(ev_response)
    
    # Handle rate-limit exceptions
    if 'errors' in ev_response_json:
        for error in ev_response_json['errors']:
            print(error)
            if int(error['status']) == 429:
                if count < 5:
                    # Wait 60 seconds for every retry
                    time.sleep(60 * (count + 1))
                    count += 1
                    print("retry - %s" % count)
                    return call_api(action, ev_create_url, data, count)
                else:
                    # Give-up after 5 retries
                    return false
            else:
                # Throw Exception and end script if any other error occurs
                raise Exception('%d - %s' % (int(error['status']), error['title']))
    
    return ev_response_json

# Helper method - get id from relationship link
# Example: http://test.host/api/v2/signatures/1003.json
# Should return 1003
def get_id(link):
    a = link.split("/")
    b = a[len(a) - 1].split(".")
    return int(b[0])

# Helper method - get page number from link
# Example: https://api.evident.io/api/v2/reports/22952488/alerts?filter%5Bstatus_eq%5D=fail&page%5Bnumber%5D=6&page%5Bsize%5D=20
# Should return 6
def get_page_number(link):
    a = link.split("page%5Bnumber%5D=")
    b = a[1].split("&")
    return int(b[0])

# Construct the email body
def construct_body(teams, signatures, total):
    body = """
Weekly Risk Summary (%(date)s)
================================
%(new_risks)d new risks identified
<a href='https://esp.evident.io/reports/alerts/latest?filter%%5Bfirst_seen%%5D=168&filter%%5Bstatus_in%%5D%%5B%%5D=fail'>new risks identified</a>
%(new_high_risks)d new risks identified
<a href='https://esp.evident.io/reports/alerts/latest?filter%%5Bfirst_seen%%5D=168&filter%%5Brisk_level_in%%5D=High&filter%%5Bstatus_in%%5D%%5B%%5D=fail'>new high risks identified</a>
%(total_risks)d total risks identified
<a href='https://esp.evident.io/reports/alerts/latest?filter%%5Bstatus_in%%5D%%5B%%5D=fail'>total risks identified</a>
           """ % {'date': datetime.today().strftime('%Y-%m-%d'), 'new_risks': total['new_risks'], 'new_high_risks': total['new_high_risks'], 'total_risks': total['total_risks']}
    
    for team_id in teams:
        team = teams[team_id]
        body += """
%(team_name)s - <a href='https://esp.evident.io/reports/alerts/latest?filter%%5Bexternal_account_team_id_eq%%5D=%(team_id)d&filter%%5Bfirst_seen%%5D=168&filter%%5Bstatus_in%%5D%%5B%%5D=fail'>view latest risks</a>
new risks identified - %(new_risks)d
new high risks identified -  %(new_high_risks)d
total risks identified - %(total_risks)d
                """ % {'team_name': team['name'], 'team_id': team_id, 'new_risks': team['new_risks'], 'new_high_risks': team['new_high_risks'], 'total_risks': team['total_risks']}
    
    top_risks = []
    # Calculate top 5 risks
    for sig_id in signatures:
        signature = signatures[sig_id]
        position = 0
        for i in range(6):
            position = i
            if i > (len(top_risks) - 1) or signature['total_risks'] > signatures[top_risks[i]]['total_risks']:
                break
        
        top_risks.insert(position, sig_id)
        
    body += "\nTop Risks - occurrences\n"
            
    for i in range(5):
        signature = signatures[top_risks[i]]
        body += "%(signature_name)s - %(total_risks)d \n" % {'signature_name': signature['name'], 'total_risks': signature['total_risks']}
        
    return body
    
# Send email
def send_email(subject, body, emails):
    global gmail_user
    global gmail_password
    
    msg = MIMEMultipart()
    msg['Subject'] = subject

    text = MIMEText(body)
    msg.attach(text)

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_user, gmail_password)
    for email in emails:
        server.sendmail(gmail_user, email, msg.as_string())
    server.close()


# === Begin Main Script ===

teams = {} # team_id - {team name, new risks, new high risks, total risks}
signatures = {} # signature_id - {signature name, identifier, total risks}
total = {'new_risks': 0,
         'new_high_risks': 0,
         'total_risks': 0} # new risks, new high risks, total risks
 
# Retrieve list of Signatures
signatures_url = 'https://api.evident.io/api/v2/signatures?page[size]=100'
while signatures_url:
    data = ''
    signatures_json = call_api('GET', signatures_url, data)
    if 'data' in signatures_json:
        for signature in signatures_json['data']:
            new_signature = {'name': signature['attributes']['name'],
                         'identifier': signature['attributes']['identifier'],
                         'total_risks': 0
                        }
            signatures[int(signature['id'])] = new_signature
        
        
    if 'links' in signatures_json and 'next' in signatures_json['links']:
        signatures_url = signatures_json['links']['next']
    else:
        signatures_url = False

# Get stats for latest team
data = ''
latest_for_teams_url = 'https://api.evident.io/api/v2/stats/latest_for_teams'
latest_for_teams_json = call_api('GET', latest_for_teams_url, data)

# Go through each external account and calculate stats
for stat in latest_for_teams_json['data']:
    new_risks = stat['attributes']['new_1w_low_fail'] + stat['attributes']['new_1w_medium_fail'] + stat['attributes']['new_1w_high_fail']
    
    # Retrieve report
    report_id = get_id(stat['relationships']['report']['links']['related'])
    report_url = stat['relationships']['report']['links']['related']
    report_json = call_api('GET', report_url, data)
    
    # Retrieve or create new team object to store risks
    team_id = get_id(report_json['data']['relationships']['team']['links']['related'])
    print("Getting stats for team %d" % team_id)
    if team_id in teams:
        team = teams[team_id]
    else:
        team_url = report_json['data']['relationships']['team']['links']['related']
        team_json = call_api('GET', team_url, data)
        team = {'name': team_json['data']['attributes']['name'],
                'new_risks': new_risks, 
                'new_high_risks': stat['attributes']['new_1w_high_fail'],
                'total_risks': 0
               }
        teams[team_id] = team
        total['new_risks'] += new_risks
        total['new_high_risks'] += stat['attributes']['new_1w_high_fail']
        
    # Retrieve failed alerts by signature
    for sig_id in signatures:
        signature = signatures[sig_id]
        print("Getting stats for signature %s" % signature['identifier'])
        alerts_url = 'https://api.evident.io/api/v2/reports/%d/alerts?page[size]=100&filter[status_eq]=fail&filter[signature_identifier_cont]=%s' % (report_id, signature['identifier'])
        alerts_json = call_api('GET', alerts_url, data)
        
        # Find last page number
        last_page_num = 1
        if 'links' in alerts_json and 'last' in alerts_json['links']:
            alerts_url = alerts_json['links']['last']
            last_page_num = get_page_num(alerts_url)
            alerts_json = call_api('GET', alerts_url, data)
            count = 100 * last_page_num
        else:
            count = 0
            
        count += len(alerts_json['data'])
        signature['total_risks'] += count
        team['total_risks'] += count
        total['total_risks'] += count

# Send email
body = construct_body(teams, signatures, total)
subject = 'Evident Security Platform: Weekly Risk Summary'
send_email(subject, body, emails)

# === End Main Script ===
