import telepot

import time, sys, datetime

from main import db, User

from hashing import check_secure_val

from gmail_api import GetMessage, ListMessagesMatchingQuery, Mail, createMessageFromMail

from oauth2client import client

from apiclient import discovery

from utilities import datetime_from_string_date

import httplib2

from daemon import Daemon

import logging
logging.basicConfig(format='%(asctime)s %(message)s',
                    level=logging.DEBUG,
                    datefmt='%m/%d/%Y %I:%M:%S %p')

class UpdateDaemon(Daemon):

    def run(self):
        with open('/home/saeidtheblind/proj/tele-gmail/bot_token.txt','r') as f:
            TOKEN = f.read().strip()
        bot = telepot.Bot(TOKEN)
        while 1:
            users = User.query.all()
            for u in users:
                db.session.refresh(u)
                logging.info('checking user %s',u.email)
                if not u.chat_id:
                    logging.info("user %s doesn't have chat_id")
                    continue
                try:
                    credentials = client.OAuth2Credentials.from_json(u.credentials)
                    http = credentials.authorize(httplib2.Http())
                    if credentials.access_token_expired:
                        logging.info("credentials for %s has expired, refreshing", u.email)
                        credentials.refresh(http)
                        u.credentials = credentials.to_json()
                        db.session.commit()
                        logging.info("successful refresh")
                    service = discovery.build('gmail', 'v1', http=http)
                    #msgs = ListMessagesWithLabels(service, u.email, maxResults=1)
                    msgs = ListMessagesMatchingQuery(service, u.email, 'after: '+u.previous)
                    if len(msgs) == 0:
                        logging.info("no new messages for %s", u.email)
                        continue
                    logging.info( 'found %d new messages',len(msgs))
                    pre_time = int(u.previous)
                    for m in msgs[::-1]:
                        message = GetMessage(service, u.email, m['id'])
                        msg_time = int(message['internalDate'])/1000
                        if msg_time <= pre_time:
                            continue
                        u.previous = msg_time
                        mail = Mail()
                        mail.snippet = message['snippet']
                        mail.internal_time = datetime.datetime.utcfromtimestamp(msg_time)
                        for x in message['payload']['headers']:
                            if x['name'] == 'Subject':
                                mail.subject = x['value']
                            #~ elif x['name'] == 'Date':
                                #~ mail.raw_date = x['value']
                                #~ print 'raw_date', x['value']
                                #~ mail.date = datetime_from_string_date(mail.raw_date)
                                #~ print 'date', mail.date
                            elif x['name'] == 'From':
                                mail.from_ = x['value']
                        bot.sendMessage(u.chat_id, createMessageFromMail(mail))
                        db.session.commit()
                except client.HttpAccessTokenRefreshError:
                    logging.info("access for %s has been revoked", u.email)
                    bot.sendMessage(u.chat_id, "Access has been revoked go to " + \
                                                "http://robotoos.ir:5000/login")
                    db.session.delete(u)
                    db.session.commit()
                    
            logging.info("sleeping")
            sys.stdout.flush()
            time.sleep(120)
            
    
if __name__ == "__main__":
    daemon = UpdateDaemon('/home/saeidtheblind/proj/tele-gmail/update_bot.pid',
                            stdin='/dev/null',
                            stdout='/home/saeidtheblind/proj/tele-gmail/update_bot.out',
                            stderr='/home/saeidtheblind/proj/tele-gmail/update_bot.err')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'run' == sys.argv[1]:
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)        
