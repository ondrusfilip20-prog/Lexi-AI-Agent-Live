import datetime
import os, os.path
import json # Essential for reading the token from the environment variable
import traceback

# DEBUG: show which calendar_service module is loaded at startup
print(f"calendar_service (root) loaded from: {__file__}")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """
    Handles Google authorization. 
    This version is designed specifically for Render and relies ONLY on 
    the GOOGLE_CALENDAR_TOKEN environment variable.
    """
    
    # Check for the deployed token
    if 'GOOGLE_CALENDAR_TOKEN' in os.environ:
        try:
            # Load credentials directly from the environment variable (JSON string)
            token_data = json.loads(os.environ['GOOGLE_CALENDAR_TOKEN'])
        except Exception as e:
            print(f"FATAL ERROR: GOOGLE_CALENDAR_TOKEN environment variable is invalid JSON: {e}")
            traceback.print_exc()
            raise

        try:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)

            # Diagnostics: print which top-level keys are present (avoid printing secrets)
            if isinstance(token_data, dict):
                print(f"DEBUG: GOOGLE_CALENDAR_TOKEN keys: {list(token_data.keys())}")

            # If credentials show expired and a refresh token exists, try to refresh.
            if getattr(creds, 'expired', False):
                print("DEBUG: Credentials appear expired.")
                if getattr(creds, 'refresh_token', None):
                    try:
                        creds.refresh(Request())
                        print("DEBUG: Credentials refreshed successfully.")
                    except Exception as e:
                        print(f"DEBUG: Failed to refresh credentials: {e}")
                        traceback.print_exc()
                        raise
                else:
                    print("DEBUG: No refresh token available in credentials; refresh not possible.")
            else:
                print("DEBUG: Credentials are valid (not expired).")

            service = build('calendar', 'v3', credentials=creds)

            # CRITICAL: Returns immediately for the successful deployment
            return service 
        except Exception as e:
            # If loading fails, give more context in the logs
            print(f"FATAL ERROR: Could not initialize calendar from GOOGLE_CALENDAR_TOKEN: {e}")
            traceback.print_exc()
            raise

    # If the environment variable is not set (should not happen on Render)
    print("FATAL ERROR: GOOGLE_CALENDAR_TOKEN environment variable not found. Calendar tool is disabled.")
    raise EnvironmentError("Calendar token not found. Cannot initialize Google Calendar.")

def find_open_slots(service, calendar_id='primary'):
    """Queries the calendar API for busy slots in the next 48 hours."""
    # Ensure local machine runs in UTC for compatibility with the API
    now = datetime.datetime.utcnow().isoformat() + 'Z' 
    end_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=48)).isoformat() + 'Z'

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found. The next 48 hours are likely open."
        else:
            busy_slots = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                busy_slots.append(f"Busy from {event.get('summary', 'No Title')}: {start} to {end}")
            
            return "\n".join(busy_slots)

    except HttpError as error:
        return f'An error occurred while fetching calendar data: {error}'