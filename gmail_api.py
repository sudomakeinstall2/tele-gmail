from apiclient import errors
from apiclient import discovery
from oauth2client import client
import httplib2

class Mail():
    pass

def createMessageFromMail(mail):
    s = ""
    s = mail.from_+ "\n" +mail.subject
    return s

def GetMessage(service, user_id, msg_id):
  """Get a Message with given ID.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    msg_id: The ID of the Message required.

  Returns:
    A Message.
  """
  try:
    message = service.users().messages().get(userId=user_id, id=msg_id).execute()

    #print 'Message snippet: %s' % message['snippet']

    return message
  except errors.HttpError, error:
    print 'An error occurred: %s' % error
    
def ListMessagesUntillId(service, user_id, msg_id):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Messages with these labelIds applied.

  Returns:
    List of Messages that have all required Labels applied. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate id to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               labelIds=[]).execute()
    messages = []
    if 'messages' in response:
        for m in response['messages']:
            if m['id'] == msg_id:
                print 'found prev1'
                break
            else:
                messages.append(m)
        else:
            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = service.users().messages().list(userId=user_id,
                                                 labelIds=[],
                                                 pageToken=page_token).execute()
                for m in response['messages']:
                    if m['id'] == msg_id:
                        print 'found prev2'
                        break
                    else:
                        messages.append(m)
                else:
                    continue
                break
        return messages        
  except errors.HttpError, error:
    print 'An error occurred: %s' % error    

def ListMessagesWithLabels(service, user_id, label_ids=[], maxResults=5):
  """List all Messages of the user's mailbox with label_ids applied.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    label_ids: Only return Messages with these labelIds applied.

  Returns:
    List of Messages that have all required Labels applied. Note that the
    returned list contains Message IDs, you must use get with the
    appropriate id to get the details of a Message.
  """
  try:
    response = service.users().messages().list(userId=user_id,
                                               labelIds=label_ids,maxResults=maxResults).execute()
    messages = []
    if 'messages' in response:
      messages.extend(response['messages'])

#    while 'nextPageToken' in response:
#      page_token = response['nextPageToken']
#      response = service.users().messages().list(userId=user_id,
#                                                 labelIds=label_ids,
#                                                 pageToken=page_token).execute()
#     messages.extend(response['messages'])
    return messages
  except errors.HttpError, error:
    print 'An error occurred: %s' % error

def ListLabels(service, user_id):
  """Get a list all labels in the user's mailbox.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.

  Returns:
    A list all Labels in the user's mailbox.
  """
  try:
    response = service.users().labels().list(userId=user_id).execute()
    labels = response['labels']
    #for label in labels:
    #  print 'Label id: %s - Label name: %s' % (label['id'], label['name'])
    return repr([label['name'] for label in labels])
  except errors.HttpError, error:
    print 'An error occurred: %s' % error

