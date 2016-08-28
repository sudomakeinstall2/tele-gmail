import telepot

import time,sys

from main import db, User

from hashing import check_secure_val

from gmail_api import GetMessage, ListMessagesWithLabels, ListMessagesUntillId, Mail, createMessageFromMail

from oauth2client import client

from apiclient import discovery

import httplib2

from daemon import Daemon

class UpdateDaemon(Daemon):

    def run(self):
        TOKEN = '265185588:AAGBUc8hn7O1RtcttDHtYikie4QLCH12mrE'
        bot = telepot.Bot(TOKEN)
        while 1:
            users = User.query.all()
            for u in users:
                print 'checking user ', u.email
                if not u.chat_id:
                    print 'user',u.email,"doesn't have chat_id"
                    continue
                credentials = client.OAuth2Credentials.from_json(u.credentials)
                http = credentials.authorize(httplib2.Http())
                if credentials.access_token_expired:
                    print 'credential for '+u.email+' has expired, refreshing'
                    credentials.refresh(http)
                    u.credentials = credentials.to_json()
                    db.session.commit()
                    print 'end refresh'
                service = discovery.build('gmail', 'v1', http=http)
                msgs = ListMessagesUntillId(service, u.email, u.previous)
                if len(msgs) == 0:
                    #bot.sendMessage(u.chat_id, 'no new messages for ' + u.email)
                    continue
                print 'found %d new messages',len(msgs)
                for m in msgs[::-1]:
                    message = GetMessage(service, u.email, m['id'])
                    u.previous = m['id']
                    mail = Mail()
                    mail.snippet = message['snippet']
                    for x in message['payload']['headers']:
                        if x['name'] == 'Subject':
                            mail.subject = x['value']
                        elif x['name'] == 'Date':
                            mail.date = x['value']
                        elif x['name'] == 'From':
                            mail.from_ = x['value']
                    bot.sendMessage(u.chat_id, createMessageFromMail(mail))
                    db.session.commit()
            print 'sleeping'
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
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)        
