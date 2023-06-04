import json
import time
import socket
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
import os


def get_sheet(spreadsheet_id, sheet_name):
    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # relative to script dir
    script_dir = os.path.dirname(__file__)
    secrets_file = os.path.join(script_dir, '../../../secrets/googlekey.json')
    creds = ServiceAccountCredentials.from_json_keyfile_name(secrets_file, scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        client.open_by_key(spreadsheet_id).add_worksheet(sheet_name, 100, 100)
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    return sheet


def edit_hostname_sheet(spreadsheet_id, sheet_name):
    sheet = get_sheet(spreadsheet_id, sheet_name)
    # get current ip using dev.get_ip()
    url = get_ngrok_url()
    # Update the specified row with the given values
    sheet.update('A1', "IP")
    sheet.update('B1', url)
    sheet.update('A2', "last update")
    sheet.update('B2', time.ctime())

def edit_main_sheet(spreadsheet_id):
    sheet = get_sheet(spreadsheet_id, "main")
    # get current ip using dev.get_ip()
    url = get_ngrok_url()
    # Update the specified row with the given values
#     find row containing hostname in column A. if not exist, add new row
    hostname = socket.gethostname()
    try:
        row = sheet.find(hostname).row
    except Exception as e:
        row = len(sheet.col_values(1)) + 1
        sheet.update(f'A{row}', hostname)
    sheet.update(f'B{row}', time.ctime())
    sheet.update(f'C{row}', url)


def get_ngrok_url():
    try:
        res = requests.get("http://localhost:4040/api/tunnels")
        # Get the JSON data from the response
        res_data = res.json()
        # Get the public URL of the first tunnel
        public_url = res_data["tunnels"][0]["public_url"]
    except Exception as e:
        return str(e)
    return public_url


def write_url_to_google_sheet():
    with open('secrets/googlesheet.json') as f:
        spreadsheet_id = json.load(f)['id']
    hostname = socket.gethostname()
    edit_hostname_sheet(spreadsheet_id, hostname)
    edit_main_sheet(spreadsheet_id)


if __name__ == '__main__':
    write_url_to_google_sheet()
