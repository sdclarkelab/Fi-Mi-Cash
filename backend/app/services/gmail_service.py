import base64
import os
import pickle
from datetime import datetime
from typing import List

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import get_settings
from app.core.exceptions import GmailAPIError
from app.core.logger import logger
from app.models.schemas import EmailMessage

settings = get_settings()


class GmailService:
    def __init__(self):
        self._service = None

    @property
    def service(self):
        if not self._service:
            self._service = self._initialize_service()
        return self._service

    def _initialize_service(self):
        try:
            creds = None
            if os.path.exists(settings.GMAIL_TOKEN_PATH):
                with open(settings.GMAIL_TOKEN_PATH, 'rb') as token:
                    creds = pickle.load(token)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.GMAIL_CREDENTIALS_PATH,
                        settings.GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                with open(settings.GMAIL_TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)

            return build('gmail', 'v1', credentials=creds)

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise GmailAPIError(f"Gmail service initialization failed: {str(e)}")

    def get_messages(self, query: str) -> List[EmailMessage]:
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query
            ).execute()

            messages = results.get('messages', [])
            return [self._fetch_email_message(msg['id']) for msg in messages]

        except Exception as e:
            logger.error(f"Failed to fetch Gmail messages: {str(e)}")
            raise GmailAPIError(f"Failed to fetch messages: {str(e)}")

    def _fetch_email_message(self, message_id: str) -> EmailMessage:
        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {
                header['name'].lower(): header['value']
                for header in msg['payload']['headers']
            }

            body = self._get_email_body(msg)

            return EmailMessage(
                subject=headers.get('subject', ''),
                sender=headers.get('from', ''),
                date=datetime.fromtimestamp(int(msg['internalDate']) / 1000),
                body=body
            )

        except Exception as e:
            logger.error(f"Failed to fetch email message: {str(e)}")
            raise GmailAPIError(f"Failed to fetch message details: {str(e)}")

    def _get_email_body(self, message: dict) -> str:
        if 'data' in message['payload']['body']:
            return base64.urlsafe_b64decode(
                message['payload']['body']['data']
            ).decode('utf-8')

        parts = message['payload'].get('parts', [])
        if parts:
            return base64.urlsafe_b64decode(
                parts[0]['body']['data']
            ).decode('utf-8')

        return ''
