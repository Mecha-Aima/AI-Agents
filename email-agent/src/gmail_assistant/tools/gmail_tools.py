from typing import List, Optional, Dict, Any, Iterator
from pathlib import Path
from pydantic import Field, BaseModel
from langchain_core.tools import tool
from datetime import datetime, timedelta
import datetime as dt
import json
import logging
import os
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.absolute()
_SECRETS_DIR = _ROOT / ".secrets"

try:
    from googleapiclient.discovery import build 
    from email.mime.text import MIMEText 
    from dateutil.parser import parse as parse_time 
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow 
    from google.auth.transport.requests import Request 

    def extract_message_part(payLoad) -> str:
        # Extract message from email body
        if payLoad.get("body", {}).get("data"):
            data = payLoad["body"]["data"]
            decoded = base64.urlsafe_b64decode(data).decode("utf-8")
            return decoded 
        
        # Extract messages from email parts
        if payLoad.get("parts"):
            text_parts = []
            for part in payLoad["parts"]:
                content = extract_message_part(part)
                if content:
                    text_parts.append(content)
            return "\n".join(text_parts)
        
        return ""
    

    def get_credentials(gmail_token=None, gmail_secret=None):
        token_path = _SECRETS_DIR / "token.json"
        token_data = None

        # Read gmail token from parameter, env variable, or local file
        if gmail_token:
            try:
                token_data = json.loads(gmail_token) if isinstance(gmail_token, str) else gmail_token
                logger.info("Using directly provided gmail_token parameter")
            except Exception as e:
                logger.warning(f"Could not parse provided gmail_token: {str(e)}")

        if token_data is None:
            env_token = os.getenv("GMAIL_TOKEN")
            if env_token:
                try:
                    token_data = json.loads(env_token)
                    logger.info("Using GMAIL_TOKEN environment variable")
                except Exception as e:
                    logger.warning(f"Could not parse GMAIL_TOKEN environment variable: {str(e)}")
        
        if token_data is None:
            if os.path.exists(token_path):
                try:
                    with open(token_path, "r") as f:
                        token_data = json.load(f)
                    logger.info(f"Using token from {token_path}")
                except Exception as e:
                    logger.warning(f"Could not load token from {token_path}: {str(e)}")
        
        if token_data is None:
            logger.error("Could not find valid token data in any location")
            return None

        # Create credentials object      
        try:
            from google.oauth2.credentials import Credentials

            credentials = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"])
            )

            credentials.authorize = lambda request: request 

            return credentials
        except Exception as e:
            logger.error(f"Error creating credentials object: {str(e)}")
            return None
        
    EmailData = Dict[str, Any]

    GMAIL_API_AVAILABLE = True

except Exception as e:
    GMAIL_API_AVAILABLE = False
    logger = logging.getLogger(__name__)
    print(f"❌ Exception occured while importing Gmail API libraries: {e}")



def fetch_group_emails(
    email_address: str,
    minutes_since: int = 30,
    gmail_token: Optional[str] = None,
    gmail_secret: Optional[str] = None,
    include_read: bool = False,
    skip_filters: bool = False,
) -> Iterator[Dict[str, Any]]:
    
    use_mock = False
    
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, using mock implementation")
        use_mock = True
    
    if not use_mock and not gmail_secret or not gmail_token:
        token_path = str(_SECRETS_DIR / "token.json")
        secrets_path = str(_SECRETS_DIR / "secrets.json")

        if not os.path.exists(token_path) and not os.path.exists(secrets_path):
            logger.warning(f"No Gmail API credentials found. Looking for token.json or secrets.json in .secrets directory")
            use_mock = True

    if use_mock:
        # For demo purposes, we return a mock email
        mock_email = {
            "from_email": "sender@example.com",
            "to_email": email_address,
            "subject": "Sample Email Subject",
            "page_content": "This is a sample email body for testing the email assistant.",
            "id": "mock-email-id-123",
            "thread_id": "mock-thread-id-123",
            "send_time": datetime.now().isoformat()
        }
        
        yield mock_email
        return
        
    
    try:
        creds = get_credentials(gmail_token, gmail_secret)

        if not creds or not hasattr(creds, "authorize"):
            logger.warning("Invalid Gmail credentials")
            logger.warning("Ensure GMAIL_TOKEN environment variable is set or token.json file exists")
            mock_email = {
                "from_email": "sender@example.com",
                "to_email": email_address,
                "subject": "Sample Email Subject",
                "page_content": "This is a sample email body for testing the email assistant.",
                "id": "mock-email-id-123",
                "thread_id": "mock-thread-id-123",
                "send_time": datetime.now().isoformat()
            }
            
            yield mock_email 
            return

        
        service = build("gmail", "v1", credentials=creds)
        after = int((datetime.now() - timedelta(minutes=minutes_since)).timestamp())

        query = f"(to:{email_address} OR from:{email_address}) after:{after}"

        if not include_read:
            query += " is:unread"
        else:
            logger.info("Including read emails in search")
        
        logger.info(f"Gmail search query: {query}")

        messages = []
        nextPageToken = None 
        logger.info(f"Fetching emails for {email_address} from last {minutes_since} minutes")

        while True:
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, pageToken=nextPageToken)
                .execute()
            )
            if "messages" in results:
                new_messages = results["messages"]
                messages.extend(new_messages)
                logger.info(f"Found {len(new_messages)} messages in this page")
            else:
                logger.info("No messages found in this page")
                
            nextPageToken = results.get("nextPageToken")
            if not nextPageToken:
                logger.info(f"Total messages found: {len(messages)}")
                break

        count = 0
        for message in messages:
            try:
                msg = service.users().messages().get(userId="me", id=message["id"]).execute()
                thread_id = msg["threadId"]
                payload = msg["payload"]
                headers = payload.get("headers", [])

                thread = service.users().threads().get(userId="me", id=thread_id).execute()
                messages_in_thread = thread["messages"]
                logger.info(f"Retrieved thread {thread_id} with {len(messages_in_thread)} messages")

                if all("internalDate" in msg for msg in messages_in_thread):
                    messages_in_thread.sort(key=lambda m: int(m.get("internalDate", 0)))
                    logger.info(f"Sorted {len(messages_in_thread)} messages by internalDate")
                else:
                    messages_in_thread.sort(key=lambda m: m["id"])
                    logger.info(f"Sorted {len(messages_in_thread)} messages by ID (internalDate missing)")

                for idx, msg in enumerate(messages_in_thread):
                    headers = msg["payload"]["headers"]
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    from_email = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown")
                    logger.info(f"  Message {idx+1}/{len(messages_in_thread)}: ID={msg['id']}, Date={date}, From={from_email}")

                logger.info(f"Thread {thread_id} has {len(messages_in_thread)} messages")

                last_message = messages_in_thread[-1]
                last_headers = last_message["payload"]["headers"]

                from_header = next(
                    header["value"] for header in last_headers if header["name"] == "From"
                )
                last_from_header = next(
                    header["value"]
                    for header in last_message["payload"].get("headers")
                    if header["name"] == "From"
                )

                if email_address in last_from_header:
                    yield {
                        "id": message["id"],
                        "thread_id": message["threadId"],
                        "user_respond": True,
                    }
                    continue

                is_from_user = email_address in from_header
                is_latest_in_thread = message["id"] == last_message["id"]

                should_process = skip_filters or (not is_from_user and is_latest_in_thread)

                if not should_process:
                    if is_from_user:
                        logger.debug(f"Skipping message {message['id']}: sent by the user")
                    elif not is_latest_in_thread:
                        logger.debug(f"Skipping message {message['id']}: not the latest in thread")

                
                if should_process:
                    # Log detailed information about this message
                    logger.info(f"Processing message {message['id']} from thread {thread_id}")
                    logger.info(f"  Is latest in thread: {is_latest_in_thread}")
                    logger.info(f"  Skip filters enabled: {skip_filters}")
                    

                    if not skip_filters:
                        # Use original message if skip_filters is False
                        process_message = message
                        process_payload = payload
                        process_headers = headers
                    else:
                        # Use the latest message in the thread if skip_filters is True
                        process_message = last_message
                        process_payload = last_message["payload"]
                        process_headers = process_payload.get("headers", [])
                        logger.info(f"Using latest message in thread: {process_message['id']}")
                    
                    # Extract email metadata from headers
                    subject = next(
                        header["value"] for header in process_headers if header["name"] == "Subject"
                    )
                    from_email = next(
                        (header["value"] for header in process_headers if header["name"] == "From"),
                        "",
                    ).strip()
                    _to_email = next(
                        (header["value"] for header in process_headers if header["name"] == "To"),
                        "",
                    ).strip()
                    
                    # Use Reply-To header if present
                    if reply_to := next(
                        (
                            header["value"]
                            for header in process_headers
                            if header["name"] == "Reply-To"
                        ),
                        "",
                    ).strip():
                        from_email = reply_to
                        
                    # Extract and parse email timestamp
                    send_time = next(
                        header["value"] for header in process_headers if header["name"] == "Date"
                    )
                    parsed_time = parse_time(send_time)
                    
                    # Extract email body content
                    body = extract_message_part(process_payload)
                    
                    # Yield the processed email data
                    yield {
                        "from_email": from_email,
                        "to_email": _to_email,
                        "subject": subject,
                        "page_content": body,
                        "id": process_message["id"],
                        "thread_id": process_message["threadId"],
                        "send_time": parsed_time.isoformat(),
                    }
                    count += 1

            except Exception as e:
                logger.warning(f"Failed to process message {message['id']}: {str(e)}")
            
        logger.info(f"Found {count} emails to process out of {len(messages)} total messages")

    except Exception as e:
        logger.error(f"Error accessing Gmail API: {str(e)}")
        mock_email = {
            "from_email": "sender@example.com",
            "to_email": email_address,
            "subject": "Sample Email Subject",
            "page_content": "This is a sample email body for testing the email assistant.",
            "id": "mock-email-id-123",
            "thread_id": "mock-thread-id-123",
            "send_time": datetime.now().isoformat()
        }
        
        yield mock_email


class FetchEmailsInput(BaseModel):
    """
    Input schema for the fetch_emails_tool.
    """
    email_address: str = Field(
        description="Email address to fetch emails for"
    )
    minutes_since: int = Field(
        default=30,
        description="Only retrieve emails newer than this many minutes"
    )

@tool(args_schema=FetchEmailsInput)
def fetch_emails_tool(email_address: str, minutes_since: int = 30) -> str:
    """
    Fetches recent emails from Gmail for the specified email address.
    
    Args:
        email_address: Email address to fetch messages for
        minutes_since: Only retrieve emails newer than this many minutes (default: 30)
        
    Returns:
        String summary of fetched emails
    """
    emails = list(fetch_group_emails(email_address, minutes_since))

    if not emails:
        return "No new emails found"
    
    result = f"Found {len(emails)} new emails:\n\n"

    for i, email in enumerate(emails, 1):
        if email.get("user_respond", False):
            result += f"{i}. You already responded to this email (Thread ID: {email['thread_id']})\n\n"
            continue 

        result += f"{i}. From: {email['from_email']}\n"
        result += f"   To: {email['to_email']}\n"
        result += f"   Subject: {email['subject']}\n"
        result += f"   Time: {email['send_time']}\n"
        result += f"   ID: {email['id']}\n"
        result += f"   Thread ID: {email['thread_id']}\n"
        result += f"   Content: {email['page_content'][:200]}...\n\n"

    return result 


class SendEmailInput(BaseModel):
    email_id: str = Field(description="Gmail message ID to reply to. This must be a valid Gmail message ID obtained from the fetch_emails_tool. If you're creating a new email (not replying), you can use any string like 'NEW_EMAIL'.")
    response_text: str = Field(description="Content of reply")
    email_address: str = Field(description="Current user's email address")
    additional_recipients: Optional[List[str]] = Field(default=None, description="Optional additional recipients to include")
    

def send_email(
        email_id: str,
        response_text: str,
        email_address: str,
        additional_recipients: Optional[List[str]] = None
) -> bool:
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, simulating email send")
        logger.info(f"Would send: {response_text[:100]}...")
        return True
    
    try:
        creds = get_credentials(
            gmail_token=os.getenv("GMAIL_TOKEN"),
            gmail_secret=os.getenv("GMAIL_SECRET")
        )
        service = build("gmail", "v1", credentials=creds)

        try:
            message = service.users().messages().get(userId="me", id=email_id).execute()
            headers = message["payload"]["headers"]

            subject = next(header["value"] for header in headers if header["name"] == "Subject")
            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            original_from = next(header["value"] for header in headers if header["name"] == "From")
            thread_id = message["threadId"]
        except Exception as e:
            logger.warning(f"Could not retrieve original message with ID {email_id}. Error: {str(e)}")
            subject = "Response"
            original_from = "recipient@example.com"  # Will be overridden by user input
            thread_id = None

        msg = MIMEText(response_text)
        msg["to"] = original_from
        msg["from"] = email_address
        msg["subject"] = subject

        if additional_recipients:
            msg["cc"] = ", ".join(additional_recipients)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        # Prepare message body
        body = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id

        # Send email
        sent_message = (
            service.users()
            .messages()
            .send(
                userId="me",
                body=body
            )
            .execute()
        )

        logger.info(f"Email sent: Message ID {sent_message['id']}")
        return True

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False
    

@tool(args_schema=SendEmailInput)
def send_email_tool(
    email_id: str,
    response_text: str,
    email_address: str,
    additional_recipients: Optional[List[str]] = None
) -> str:
    """
    Send a reply to an existing email thread or create a new email in Gmail.
    
    Args:
        email_id: Gmail message ID to reply to. This should be a valid Gmail message ID obtained from the fetch_emails_tool. 
                 If creating a new email rather than replying, you can use any string identifier like "NEW_EMAIL".
        response_text: Content of the reply or new email
        email_address: Current user's email address (the sender)
        additional_recipients: Optional additional recipients to include
        
    Returns:
        Confirmation message
    """
    try:
        success = send_email(
            email_id,
            response_text,
            email_address,
            additional_recipients=additional_recipients
        )

        if success:
            return f"Email reply sent successfully to message ID: {email_id}"
        else:
            return "Failed to send email due to an API error"
    
    except Exception as e:
        return f"Failed to send email: {str(e)}"
    

class CheckCalendarInput(BaseModel):
    """
    Input schema for the check_calendar_tool.
    """
    dates: List[str] = Field(
        description="List of dates to check in DD-MM-YYYY format"
    )


def get_calendar_events(dates: List[str]) -> str:
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, returning null")
        return 
    
    try:
        creds = get_credentials(
            gmail_secret=os.getenv("GMAIL_SECRET"),
            gmail_token=os.getenv("GMAIL_TOKEN")
        )
        service = build("calendar", "v3", credentials=creds)
        result = "Calendar events:\n\n"

        for date_str in dates:
             # Parse date string (DD-MM-YYYY)
            day, month, year = date_str.split("-")

            start_time = f"{year}-{month}-{day}T00:00:00Z"
            end_time = f"{year}-{month}-{day}T23:59:59Z"

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_time,
                    timeMax=end_time,
                    singleEvents=True,
                    orderBy="startTime"
                )
                .execute()
            )

            events = events_result.get("items", [])
            result += f"Events for {date_str}:\n"

            if not events:
                result += "  No events found for this day\n"
                result += "  Available all day\n\n"
                continue

            busy_slots = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                
                # Convert to datetime objects
                if "T" in start:  # dateTime format
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                    # Ensure timezone-aware datetimes; default to UTC if missing tzinfo
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=dt.timezone.utc)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=dt.timezone.utc)
                    
                    # Format for display
                    start_display = start_dt.strftime("%I:%M %p")
                    end_display = end_dt.strftime("%I:%M %p")
                    
                    result += f"  - {start_display} - {end_display}: {event['summary']}\n"
                    busy_slots.append((start_dt, end_dt))
                else:  # all-day event
                    result += f"  - All day: {event['summary']}\n"
                    busy_slots.append(("all-day", "all-day"))

            if "all-day" in [slot[0] for slot in busy_slots]:
                result += "  Available: No availability (all-day events)\n\n"
            else:
                busy_slots.sort(key=lambda x: x[0])
                # Ensure working hours are timezone-aware (UTC) to match event datetimes
                work_start = datetime(
                    year=int(year), 
                    month=int(month), 
                    day=int(day), 
                    hour=9, 
                    minute=0,
                    tzinfo=dt.timezone.utc,
                )
                work_end = datetime(
                    year=int(year), 
                    month=int(month), 
                    day=int(day), 
                    hour=17, 
                    minute=0,
                    tzinfo=dt.timezone.utc,
                )

                available_slots = []
                current = work_start
                
                for start, end in busy_slots:
                    if current < start:
                        available_slots.append((current, start))
                    current = max(current, end)
                
                if current < work_end:
                    available_slots.append((current, work_end))

                if available_slots:
                    result += "  Available: "
                    for i, (start, end) in enumerate(available_slots):
                        start_display = start.strftime("%I:%M %p")
                        end_display = end.strftime("%I:%M %p")
                        result += f"{start_display} - {end_display}"
                        if i < len(available_slots) - 1:
                            result += ", "
                    result += "\n\n"
                else:
                    result += "  Available: No availability during working hours\n\n"

        return result

    except Exception as e:
        logger.error(f"Error checking calendar: {str(e)}")
        return 
    

@tool(args_schema=CheckCalendarInput)
def check_calendar_tool(dates: List[str]) -> str:
    """
    Check Google Calendar for events on specified dates.
    
    Args:
        dates: List of dates to check in DD-MM-YYYY format
        
    Returns:
        Formatted calendar events for the specified dates
    """
    try:
        events = get_calendar_events(dates)
        return events
    except Exception as e:
        return f"Failed to check calendar: {str(e)}"


class ScheduleMeetingInput(BaseModel):
    """
    Input schema for the schedule_meeting_tool.
    """
    attendees: List[str] = Field(description="Email addresses of meeting attendees")
    title: str = Field(description="Meeting title/subject")
    start_time: str = Field(description="Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)")
    end_time: str = Field(description="Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)")
    organizer_email: str = Field(description="Email address of the meeting organizer")
    timezone: str = Field(description="Timezone for the meeting", default="America/New_York")


def send_calendar_invite(
        attendees: List[str],
        title: str,
        start_time: str,
        end_time: str,
        organizer_email: str,
        timezone: str = "America/New_York" 
) -> bool:
    """
    Schedule a meeting with Google Calendar and send invites.
    
    Args:
        attendees: Email addresses of meeting attendees
        title: Meeting title/subject
        start_time: Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)
        organizer_email: Email address of the meeting organizer
        timezone: Timezone for the meeting
        
    Returns:
        Success flag (True if meeting was scheduled)
    """
    if not GMAIL_API_AVAILABLE:
        logger.info("Gmail API not available, returning False")
        return False
    
    try:
        creds = get_credentials(
            gmail_secret=os.getenv("GMAIL_SECRET"),
            gmail_token=os.getenv("GMAIL_TOKEN")
        )
        service = build("calendar", "v3", credentials=creds)

        event = {
            "summary": title,
            "start": {
                "dateTime": start_time,
                "timeZone": timezone
            },
            "end": {
                "dateTime": end_time,
                "timeZone": timezone
            },
            "attendees": [{"email": email} for email in attendees],
            "organizer": {
                "email": organizer_email,
                "self": True,
            },
            "reminders": {
                "useDefault": True,
            },
            "sendUpdates": "all"
        }

        event = service.events().insert(calendarId="primary", body=event).execute()

        logger.info(f"Meeting created: {event.get("htmlLink")}")
        return True 
    except Exception as e:
        logger.error(f"Error scheduling meeting: {str(e)}")
        return False
    

@tool(args_schema=ScheduleMeetingInput)
def schedule_meeting_tool(
    attendees: List[str],
    title: str,
    start_time: str,
    end_time: str,
    organizer_email: str,
    timezone: str = "America/New_York"
) -> str:
    """
    Schedule a meeting with Google Calendar and send invites.
    
    Args:
        attendees: Email addresses of meeting attendees
        title: Meeting title/subject
        start_time: Meeting start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: Meeting end time in ISO format (YYYY-MM-DDTHH:MM:SS)
        organizer_email: Email address of the meeting organizer
        timezone: Timezone for the meeting (default: America/Los_Angeles)
        
    Returns:
        Success or failure message
    """
    try:
        success = send_calendar_invite(
            attendees,
            title,
            start_time,
            end_time,
            organizer_email,
            timezone 
        )

        if success:
            return f"Meeting '{title}' scheduled successfully"
        else:
            return "Failed to schedule meeting"

    except Exception as e:
        return f"Failed to schedule meeting: {str(e)}"
    

def mark_as_read(
    message_id,
    gmail_token: str | None = None,
    gmail_secret: str | None = None
):
    creds = get_credentials(gmail_token, gmail_secret)

    service = build("gmail", "v1", credentials=creds)
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()