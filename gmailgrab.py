#!/usr/bin/env python

"""
This pulls down a list of every message in your gmail inbox. Then,
it iterates through all messages which have attachments and downloads them
to a directory you specify.
"""

import httplib2
import os
import base64
import json

import argparse
from apiclient import discovery, errors
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

PARSER = argparse.ArgumentParser(parents=[tools.argparser])
PARSER.add_argument("-d", dest="target_dir", help="directory to write attachment files into",
                    type=str)
FLAGS = PARSER.parse_args()

# If modifying these scopes, delete your previously saved credentials
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'  # never check this in
APPLICATION_NAME = 'gmailgrab'


from functools import wraps

def backoff(func):
    """Apply exponential backoff to errors."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        msg = 'TODO: make this'
        print(msg)
        return msg
    return wrapped


class Cache(object):
    """Cache results of expensive API calls and provide those results here.
    Every message ID is unique.
    Every message can have zero or more attachments, each with their own ID.
    Each attachment ID has a filename and size.

    structure:
    {message_id: [{attachment_id_1: 12345, size: 1000}, {attachment_id_2: 34567, size: 5049}]

    }

    """
    def __init__(self):
        pass

    def exists(self):
        pass




def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'gmail-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if FLAGS:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def ListMessagesMatchingQuery(service, user_id, query=''):
    """List all Messages of the user's mailbox matching the query.

    Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    query: String used to filter messages returned.
    Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
    List of Messages that match the criteria of the query. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id,
                                                   q=query).execute()  # API call
        messages = []
        if 'messages' in response:
            messages.extend(response['messages'])

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query,
                                                       pageToken=page_token).execute()  #API call
            messages.extend(response['messages'])

        return messages
    except errors.HttpError as error:
        print('An error occurred: %s' % error)


def GetAttachments(service, user_id, msg_id, store_dir):
  """Get and store attachment from Message with given id.
  """
  try:
      message = service.users().messages().get(userId=user_id, id=msg_id).execute()  # API call

      attach_ids = []  # list of tuples
      for part in message['payload']['parts']:
          if part.get('filename') and part.get('filename').endswith('.jpg'):
              # It's listing a file name, so it's an attachment.
              attach_ids.append((part.get('filename'), part['body'].get('attachmentId')))

      # Once we have all attachment IDs, we can get each attachment.
      for basename, at_id in attach_ids:
          # TODO this check is weak. Files of same name? Use md5 or size instead..
          if os.path.exists(''.join([store_dir, basename])):
              print('File %s already exists. Skipping...' % basename)
              continue  # Save an API call
          response = service.users().messages().attachments().get(userId=user_id, messageId=msg_id, id=at_id).execute()
          file_data = base64.urlsafe_b64decode(response['data'].encode('UTF-8'))
          path = ''.join([store_dir, basename])

          with open(path, 'wb+') as f:
              f.write(file_data)
              print('wrote file: %s' % basename)

  except errors.HttpError as error:
      print('An error occurred: %s' % error)


def main():
    """snag a bunch of attachments!
    """
    output_directory = FLAGS.target_dir
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)

    # TODO: eventually take args to grab stuff from another account.
    messages = ListMessagesMatchingQuery(service, user_id='me', query='filename:*.jpg')
    print("%s messages will be searched..." % len(messages))

    # messages come back as a list of dicts. {messageId, threadId}
    # [{'id': 'ff4153f38e13f8c', 'threadId': 'ff324ef53f5ccfc'},
    # {'id': 'ff3cfaa504d5597', 'threadId': 'ff3cfaa504d5597'}]

    # TODO: exponential backoff in the event of 5xx errors, raise for 4xx.
    for message in messages:
        mid = message.get('id')
        print('Operating on message ID: %s' % mid)
        GetAttachments(service, user_id='me', msg_id=id, store_dir=output_directory)

if __name__ == '__main__':
    main()