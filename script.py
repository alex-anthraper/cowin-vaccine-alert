import email
import smtplib
from datetime import datetime
from time import sleep
import pandas as pd
import twilio
import requests

from twilio.rest import Client

mail_list = pd.read_json('mail_list.json')
to_list = mail_list['mail_list']

mail_creds = pd.read_json('email_creds.json')
username = mail_creds.email_creds.username
password = mail_creds.email_creds.password

# Your Account SID from twilio.com/console
account_sid = "AC494b263560f406c0b39ccb8d623b7140"
# Your Auth Token from twilio.com/console
auth_token  = "cb08ebfe446b7fc21aca4ece59914ed1"
client = Client(account_sid, auth_token)

from_whatsapp_no = '+13215172192'
my_whatsapp_no = '+971565483706'

def create_session_info(center, session):
    return {"district_name":center["district_name"],
            "block_name":center["block_name"],
            "name": center["name"],
            "date": session["date"],
            "capacity": session["available_capacity"],
            "age_limit": session["min_age_limit"]}

def get_sessions(data):
    for center in data["centers"]:
        for session in center["sessions"]:
            yield create_session_info(center, session)

def is_available(session):
    return session["capacity"] > 0

def is_age_plus(session, age):
    return session["age_limit"] == age

def get_for_seven_days(district_id, start_date, age):
    url = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict"
    params = {"district_id": district_id, "date": start_date.strftime("%d-%m-%Y")}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"}
    resp = requests.get(url, params=params, headers=headers)
    data = resp.json()
    return [session for session in get_sessions(data) if is_age_plus(session, age) and is_available(session)]

def create_output(session_info):
    return f"{session_info['district_name']}-{session_info['block_name']}-{session_info['name']}-{session_info['date']} ({session_info['capacity']})"


def final_list(district_id):
    content18 = "\n".join([create_output(session_info) for session_info in get_for_seven_days(district_id, datetime.today(), 18)])
    content45 = "\n".join([create_output(session_info) for session_info in get_for_seven_days(district_id, datetime.today(), 45)])
    #print(content18, content45)

    if not (content18 or content45):
        print("No availability")
    else:
        header = "\nVaccine availability as on %s" %datetime.today().strftime("%d-%m-%Y %H:%M")
        body = "\nAge: Above 18 yrs\n%s \nAge: Above 45 yrs\n%s, "%(content18, content45)
        message = header + body
        return message

def send_sms(to_no, message):
    if not message:
        print("Empty message - sms not sent")
    else:
        if len(message) >= 1500:
            truncated_msg = message[0:1500]
        else:
            truncated_msg = message[:]
        print(truncated_msg)
        client.messages.create(body=truncated_msg,
                        from_=from_whatsapp_no,
                        to=to_no)
        print("message sent")

def send_email(to_email, email_header, message):
    if not message:
        print("Empty message - e-mail not sent")
    else:
        email_msg = email.message.EmailMessage()
        email_msg["Subject"] = "Vaccination Slots Open at %s" %email_header
        email_msg["From"] = username
        email_msg["To"] = to_email
        email_msg.set_content(message)

        with smtplib.SMTP(host='smtp.gmail.com', port='587') as server:
            server.starttls()
            server.login(username, password)
            server.send_message(email_msg, username, to_email)
        
        print(message)
        print("message sent")

while True:
    for i in to_list:
        district_id = i['district_id']
        district_name = i['district_name']
        print("\n" + district_name + "-" + str(datetime.today()))
        list_to_print = final_list(district_id)
        #print(list_to_print)
        recipients = i['recipients']
        for recipient in recipients:
            to_email = recipient['email']
            send_email(to_email, district_name, list_to_print)
        sleep(5)
    sleep(60*10)

