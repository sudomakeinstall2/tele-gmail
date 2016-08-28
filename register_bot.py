import sys
import time
import telepot

from main import db, User

from hashing import check_secure_val

from gmail_api import GetMessage, ListMessagesWithLabels, Mail, createMessageFromMail

from oauth2client import client

from apiclient import discovery

from daemon import Daemon

import httplib2

class RegisterDaemon(Daemon):

    def register(self, code, chat_id):
        user_id = check_secure_val(code)
        if not user_id:
            print 'code not right'
            return False
        user = User.query.filter_by(user_id = user_id).first()
        if not user:
            print 'user not right'
            return False
        if not user.chat_id or not user.previous:
            print 'init user in db'
            user.chat_id = chat_id
            credentials = client.OAuth2Credentials.from_json(user.credentials)
            if credentials.access_token_expired:
                self.bot.sendMessage(chat_id, 'credentials expired')
                return False
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('gmail', 'v1', http=http)
            l = ListMessagesWithLabels(service, user.email, maxResults=1)
            mails = []
            for m in l:
                message = GetMessage(service, user.email, m['id'])
                user.previous = m['id']
                mail = Mail()
                mail.snippet = message['snippet']
                for x in message['payload']['headers']:
                    if x['name'] == 'Subject':
                        mail.subject = x['value']
                    elif x['name'] == 'Date':
                        mail.date = x['value']
                    elif x['name'] == 'From':
                        mail.from_ = x['value']
                self.bot.sendMessage(chat_id, createMessageFromMail(mail))

                print 'previous id email', user.previous
            db.session.commit()
            return True

    def handle(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        print(content_type, chat_type, chat_id)

        if content_type == 'text':
            #bot.sendMessage(chat_id, msg['text'])
            if msg['text'] == '/start':
                self.bot.sendMessage(chat_id, 'http://robotoos.ir:5000/login')
            elif msg['text'].split(' ')[0] == '/register':
                if len(msg['text'].split(' ')) != 2:
                    self.bot.sendMessage(chat_id, 'you need to send your registeration code')
                else:
                    if self.register(msg['text'].split(' ')[1], chat_id):
                        self.bot.sendMessage(chat_id, 'register successful')
                    else:
                        self.bot.sendMessage(chat_id, 'register failed')

    def run(self):   

        TOKEN = '265185588:AAGBUc8hn7O1RtcttDHtYikie4QLCH12mrE'

        self.bot = telepot.Bot(TOKEN)
        self.bot.message_loop(self.handle)
        print 'Listening'
        

        # Keep the program running.
        while 1:    
            time.sleep(120)
            sys.stdout.flush()
    
    

if __name__ == "__main__":
    daemon = RegisterDaemon('/home/saeidtheblind/proj/tele-gmail/register_bot.pid',
                            stdin='/dev/null',
                            stdout='/home/saeidtheblind/proj/tele-gmail/register_bot.out',
                            stderr='/home/saeidtheblind/proj/tele-gmail/register_bot.err')
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
    
    
