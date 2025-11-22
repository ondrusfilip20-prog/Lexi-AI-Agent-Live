import datetime
import os
import json

# DEBUG: show which calendar_service module is loaded at startup
print(f"calendar_service (lexi-agent) loaded from: {__file__}")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

def get_calendar_service():
    """Handles Google login/authorization and returns the calendar API service object."""
    # First try to load credentials from the environment (for deployments)
    if 'GOOGLE_CALENDAR_TOKEN' in os.environ:
        try:
            token_data = json.loads(os.environ['GOOGLE_CALENDAR_TOKEN'])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"Failed to load GOOGLE_CALENDAR_TOKEN: {e}")
            raise
    else:
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service

def find_open_slots(service, calendar_id='primary'):
    """Queries the calendar API for busy slots in the next 48 hours."""
    
    now = datetime.datetime.utcnow().isoformat() + 'Z' 
    
    tomorrow = datetime.datetime.utcnow().date() + datetime.timedelta(days=2)
    time_max = datetime.datetime.combine(tomorrow, datetime.time(23, 59, 59)).isoformat() + 'Z'
    
    body = {
        "timeMin": now,
        "timeMax": time_max,
        "items": [{"id": calendar_id}]
    }

    try:
        events_result = service.freebusy().query(body=body).execute()
        busy_slots = events_result['calendars'][calendar_id]['busy']
        
        if busy_slots:
            formatted_slots = []
            for slot in busy_slots[:3]: 
                # Convert UTC time to a more readable format
                start_time = datetime.datetime.fromisoformat(slot['start'].replace('Z', '+00:00')).strftime('%A, %I:%M %p')
                end_time = datetime.datetime.fromisoformat(slot['end'].replace('Z', '+00:00')).strftime('%I:%M %p')
                formatted_slots.append(f"OCCUPIED: {start_time} - {end_time} UTC")

            return formatted_slots
        else:
            return ["Calendar is completely open for the next 48 hours!"]
            
    except Exception as e:
        return [f"Error checking calendar: {e}"]