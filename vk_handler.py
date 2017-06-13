# -*- coding: utf-8 -*-

import urllib3
import time
import os
import logging

import vk
import telepot

from config import config

http = urllib3.PoolManager()
logging.basicConfig(filename='_log.txt', level=logging.INFO)


class VKMessages:

    def __init__(self, app_id='', user_login='', user_password='', scope=''):

        self.session = vk.AuthSession(app_id, user_login, user_password, scope)
        self.api = vk.API(self.session)
        self.mid = None
        self.bot = telepot.Bot(config.BOT_TOKEN)

    def mid_check(self, msg):              # Checks id of a message to decide, whether or not we handle it
        if self.mid is None or self.mid < msg['mid']:
            self.mid = msg['mid']
            return True
        else:
            return False

    def attachments_handle(self, attach):
        if attach['type'] == 'photo':                                   # Photo Handle
            photo_url = attach['photo']['src_big']
            self.bot.sendPhoto(config.TG_CHATID, photo_url)
            return photo_url
        elif attach['type'] == 'video':                                 # Video Handle
            video_url = 'http://vk.com/video%i_%i' % (attach['video']['owner_id'],
                                                      attach['video']['vid'])
            self.bot.sendMessage(config.TG_CHATID, video_url)
            return video_url
        elif attach['type'] == 'audio':                                 # Audio Handle
            if 'content_restricted' in attach['audio']:
                audio_file = '[ERROR]<i>%s - %s</i> is copyrighted. Cannot reach .mp3 file.' % (
                    attach['audio']['artist'],attach['audio']['title'])
                self.bot.sendMessage(config.TG_CHATID, audio_file, parse_mode='html')
                return audio_file
            else:
                audio_bytes = http.request('GET', attach['audio']['url'], preload_content=False)
                self.bot.sendAudio(config.TG_CHATID,
                                   attach['audio']['url'],
                                   performer=attach['audio']['artist'],
                                   title=attach['audio']['title'])
                audio_bytes.release_conn()
                return audio_bytes
        elif attach['type'] == 'doc':                                   # Documents Handle
            if attach['doc']['title'].endswith('.gif'):
                gif_url = http.request('GET', attach['doc']['url'])
                with open('file.gif', 'w+b') as out:
                    out.write(gif_url.data)
                    out.flush()
                    os.fsync(out.fileno())
                    out.seek(0, 0)
                    self.bot.sendDocument(config.TG_CHATID, out)
                return "Sent .gif file: %s" % (attach['doc']['title'])
            else:
                doc_url = 'Document name %s: %s' % (attach['doc']['title'], attach['doc']['url'])
                self.bot.sendMessage(config.TG_CHATID, doc_url)
                return doc_url
        elif attach['type'] == 'link':                                  # URL Handle
            link_url = attach['link']['url']
            self.bot.sendMessage(config.TG_CHATID, link_url)
            return link_url
        elif attach['type'] == 'wall':                                  # Wallposts Handle
            wall = []
            if 'text' in attach['wall']:
                text = attach['wall']['text']
                if text:
                    self.bot.sendMessage(config.TG_CHATID, text)
            if 'attachments' in attach['wall']:
                for w_attach in attach['wall']['attachments']:
                    wall_attach = self.attachments_handle(w_attach)
                    return wall_attach
            return wall
        elif attach['type'] == 'sticker':                               # Stickers Handle
            sticker_url = http.request('GET', attach['sticker']['photo_512'])
            with open('sticker.webp', 'w+b') as out:
                out.write(sticker_url.data)
                out.flush()
                os.fsync(out.fileno())
                out.seek(0, 0)
                self.bot.sendSticker(config.TG_CHATID, out)
            sticker_url.release_conn()
            return sticker_url
        elif attach['type'] == 'market' or attach['type'] == 'market_album':                    # Unsupported stuff
            self.bot.sendMessage(config.TG_CHATID, '[ERROR]Market stuff is not implemented')    # TODO: Add support?
            return '[ERROR]Market stuff is not implemented'
        elif attach['type'] == 'wall_reply':
            self.bot.sendMessage(config.TG_CHATID, '[ERROR]Wall reply not implemented')
            return "[ERROR]Wall reply not implemented"

    def fwd_message_handle(self, fwd_msg):                                                      # Forward_msg Handle
        for msg in fwd_msg:
            user_info = self.api.users.get(user_ids=msg['uid'])[0]
            message = '<b>--->%s %s:</b> %s' % (user_info['first_name'],
                                                user_info['last_name'],
                                                msg['body'])
            logging.info('Got message')
            self.bot.sendMessage(config.TG_CHATID, message, parse_mode='html')
            if 'attachments' in msg:
                for attach in msg['attachments']:
                    msg_attach = self.attachments_handle(attach)
                    logging.info(msg_attach)
            if 'fwd_messages' in msg:
                time.sleep(0.5)
                self.fwd_message_handle(msg['fwd_messages'])
            time.sleep(0.5)

        pass

    def message_handle(self, vk_msg, chat_info):
        for msgList in reversed(vk_msg['messages']):
            if type(msgList) is int:
                pass
            elif self.mid_check(msgList) and 'chat_id' in msgList and msgList['chat_id'] == chat_info['chat_id']:
                user_info = self.api.users.get(user_ids=msgList['uid'])[0]
                message = '<b>%s %s:</b> %s' % (user_info['first_name'],
                                                user_info['last_name'],
                                                msgList['body'])
                self.bot.sendMessage(config.TG_CHATID, message, parse_mode='html')
                logging.info('Got message')
                if 'attachments' in msgList:
                    for attach in msgList['attachments']:
                        msg_attach = self.attachments_handle(attach)
                        logging.info(msg_attach)
                if 'fwd_messages' in msgList:
                    logging.info('Forwarded messages:')
                    self.fwd_message_handle(msgList['fwd_messages'])

    def message_loop(self):
        try:
            ts_adr = self.api.messages.getLongPollServer()['ts']
            chat_info = self.api.messages.getChat(chat_id=config.VK_CHATID)
            while True:
                vk_msg = self.api.messages.getLongPollHistory(key=self.session.access_token,
                                                              server='imv4.vk.com/im0402',
                                                              ts=ts_adr,
                                                              mode=2)

                self.message_handle(vk_msg, chat_info)
                time.sleep(1)
        except Exception as e:
            logging.warning(e)
            return

    def __repr__(self):
        return '<vkapi_session object>'

vk_api = VKMessages(
    app_id=config.VK_APPID,
    user_login=config.VK_LOGIN,
    user_password=config.VK_PASSWD,
    scope="wall,messages")

while True:
    vk_api.message_loop()
