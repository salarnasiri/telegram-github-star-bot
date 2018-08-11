#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.
"""
This Bot uses the Updater class to handle the bot.
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
from time import sleep

import os
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot, MessageEntity)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)

from request import GithubRequest
from utils import *

from models import User, Github, Secret, db, Submit
import logging

TOKEN = "your bot token"
bot = Bot(token=TOKEN)
# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

request = GithubRequest()

db.connect()
db.create_tables([User, Github, Secret, Submit])


def set_star(bot, job):
    context = job.context
    token, repo_owner, repo_name, chat_id, secret_owner_chat_id = context["token"], context["repo_owner"], context[
        "repo_name"], context[
                                                                      'chat_id'], context['secret_owner_chat_id']
    secret_obj = Secret.get_or_none(secret=token)
    submit_obj = Submit.get_or_none(secret_id=secret_obj.id, repo_name=repo_name, repo_owner=repo_owner)
    if not submit_obj:
        submit_obj = Submit.create(secret_id=secret_obj.id, repo_name=repo_name, repo_owner=repo_owner)
    max_try = context["try"]
    while max_try <= Const.MAX_TRY:
        try:
            result = request.set_star_by_token(token, repo_owner, repo_name)
        except:
            result = False
        submit_obj.is_submitted = result
        submit_obj.save()
        if not result:
            max_try += 1
            sleep(5)
            continue
        bot.sendMessage(secret_owner_chat_id, u"ریپو %s توسط شما ستاره گرفت." % repo_name)
        bot.sendMessage("38671067", u"ریپو %s/%s توسط کاربر %s مورد ستاره گرفتن واقع شد" % (
            repo_name, repo_owner, secret_owner_chat_id))
        break

    else:
        bot.sendMessage(secret_owner_chat_id, u"بعد از %d بار تلاش نتونستیم از طرف شما ریپو %s رو ستاره دار کنیم" % (
            max_try, repo_name))


def start(bot, update, user_data):
    reply_keyboard = [['Github', 'Secrets']]
    update.message.reply_text(
        u' برای ارسال لینک اسم سایتش و برای'
        u' توکن secrets رو بزن',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard))
    user = update.message.from_user
    user_obj = User.get_or_none(first_name=user.first_name, uid=user.id)
    if not user_obj:
        user_obj = User.create(first_name=user.first_name, uid=user.id)
        user_obj.save()
    user_data['id'] = user_obj.id
    logger.info(u"user: %s registered with uid: %d", user_obj.first_name, user_obj.uid)

    return State.START


def github(bot, update, user_data):
    user = update.message.from_user
    logger.debug("user: %s select github", user.first_name)

    secret_obj = Secret.get_or_none(owner_id=user_data['id'])

    if not secret_obj or secret_obj.secret is None:
        logger.debug("user: %s has no secret", user.first_name)
        reply_keyboard = [['Secrets']]
        update.message.reply_text(u'دیر اومدی نخوا زود برو!!\n'
                                  u'اول اجازه لازم برای ستاره دادن از طرف خودت رو بده بعدش بیا اینجا',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard))

        return State.START
    update.message.reply_text(u'مثل نمونه های زیر یا لینک ریپو رو بده یا اسمشو\n'
                              u'sample\n'
                              u'https://github.com/salarnasiri/ijust_server\n'
                              u'OR\n'
                              u'salarnasiri:ijust_server',
                              reply_markup=ReplyKeyboardRemove())

    return State.GITHUB_LINK


def get_github_link(bot, update, user_data, job_queue):
    user = update.message.from_user
    logger.debug("user: %s  bye bye! after submit a github link", user.first_name)
    update.message.reply_text(u' با تشکر بعد از بررسی لینک داخل کانال @channel گذاشته میشه\n'
                              u'و همچنین برای تمای کاربرا ارسال میشه تا بعد از تاییدشون ستاره بگیری برای شر.ع دوباره /start رو بزن',
                              reply_markup=ReplyKeyboardRemove())

    message = update.message.text
    logger.debug("message %s", message)

    if "github.com" in message:
        link = message
        temp_list = message.split("/")
        logger.debug("temp %s", temp_list)
        if temp_list[-1] == "":
            temp_list.pop()
        logger.debug("temp %s", temp_list)

        repo_name = temp_list[-1]
        repo_owner = temp_list[-2]

        logger.debug("github_obj.repo_name %s", repo_name)
        logger.debug("github_obj.repo_owner %s", repo_owner)

        logger.info("user: %s send a github link: %s", user.first_name, message)

    else:
        repo_owner, repo_name = message.split(":")
        link = SitePrefix.GITHUB + "/" + repo_owner + "/" + repo_name
        logger.info("user: %s send a github owner: %s repo: %s", user.first_name, repo_owner,
                    repo_name)

    github_obj = Github.get_or_none(owner_id=user_data['id'], link=link, repo_name=repo_name, repo_owner=repo_owner)
    if not github_obj:
        github_obj = Github.create(owner_id=user_data['id'], link=link, repo_name=repo_name, repo_owner=repo_owner)
    github_obj.save()
    logger.debug("github object saved")

    after = 1
    user_data['jobs'] = []
    for _secret in Secret.select().where(Secret.permitted == True):
        context = {
            "token": _secret.secret,
            "chat_id": user.id,
            "secret_owner_chat_id": _secret.owner.uid,
            "repo_name": repo_name,
            "repo_owner": repo_owner,
            "try": 0
        }
        job = job_queue.run_once(set_star, after, context=context)

        user_data['jobs'].append({
            "job": job,
            "context": context
        })
        after += Const.REQUEST_DELAY

        logger.info("secret owner name: %s staring owner: %s repo: %s", _secret.owner.first_name, github_obj.repo_owner,
                    github_obj.repo_name)

    return ConversationHandler.END


def secret(bot, update):
    reply_keyboard = [['MyTokens', 'NewToken']]

    user = update.message.from_user
    logger.debug("user: %s select secret", user.first_name)
    update.message.reply_text(u"انتخاب کن: ",
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard))

    return State.GITHUB_SECRET


def github_history_token(bot, update, user_data):
    user = update.message.from_user
    logger.debug("User %s getting history", user.first_name)
    c = 1
    user_data['tokens'] = {}
    message = u"روی هرکدوم که بزنی پاک میشه!!!!! برای بازگشت کنسل رو بزن \n"
    entities = []
    for _secret in Secret.select().where(Secret.owner_id == user_data['id']):
        entity = MessageEntity('code', len(message) + 1 + len(str(c)) + 1 + len(_secret.user_name) + 1, 17)
        entities.append(entity)
        message += u"/%d %s %s....%s\n" % (c, _secret.user_name, _secret.secret[:9], _secret.secret[-4:])
        user_data['tokens'][c] = _secret.id
        c += 1
    else:
        message = u"تا حالا چیزی اضافه نکردی\n"
    message += u"/cancel"
    bot.sendMessage(user.id, message,
                    reply_markup=ReplyKeyboardRemove())
    return State.GITHUB_HISTORY


def github_delletin_from_history_token(bot, update, user_data):
    user = update.message.from_user
    logger.debug("User %s deleting from history", user.first_name)
    try:
        number = int(update.message.text[1:])
        _id = user_data['tokens'][number]
    except:
        logger.error("User %s sends wrong number for deleting secret: %s", user.first_name, update.message.text)
        update.message.reply_text(u"اشتباهی رخ داده از داده های خود مطمپن شوید",
                                  reply_markup=ReplyKeyboardRemove())
        return State.GITHUB_HISTORY

    secret_obj = Secret.get_or_none(id=_id)
    logger.info("User %s deleting instance secret with username: %s", user.first_name, secret_obj.user_name)
    secret_obj.delete_instance()

    update.message.reply_text(u"با موفقیت پاک شد \n برای شروع /start را بزنین",
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def github_get_secret_token(bot, update, user_data):
    user = update.message.from_user
    logger.debug("User %s sending token", user.first_name)
    secret_obj = Secret.create(owner_id=user_data['id'], site_type=Site.GITHUB, secret_type=SecretType.TOKEN)
    user_data['last_secret'] = secret_obj.id
    user_data['get_token_try'] = 0
    logger.debug("secret %s with secret type: %d", secret_obj.site_type, secret_obj.secret_type)

    update.message.reply_text(u'روی لینک زیر کلیک کنید\n'
                              u'بعد از لاگین کردن توی گیت هابتون روی توی صفحه باز شده یه عنوان برای کلیدتون بذارین مثلا :iustgithubbot_token\n'
                              u'از دسترسی های مربوط به repo دسترسی public_repo رو تیک بزنین.\n'
                              u'Generate token  رو بزنین و توکن رو برای ما ارسال کنین'
                              u'https://github.com/settings/tokens/new',
                              reply_markup=ReplyKeyboardRemove())

    return State.GITHUB_TOKEN


def github_access_auto_staring(bot, update, user_data):
    user = update.message.from_user
    logger.debug("User %s select github in secret site list", user.first_name)
    secret_obj = Secret.get_or_none(id=user_data['last_secret'])
    update.message.reply_text(u'در حال چک کردن هستیم لطفا صبور باشین')
    max_try = user_data['get_token_try']
    while max_try <= Const.MAX_TRY:
        try:
            response, result_boolean = request.get_user_by_token(update.message.text)
            break
        except Exception as e:
            max_try += 1
            return State.GITHUB_TOKEN
    else:
        update.message.reply_text(u'خطا در اتصال به سرور گیت هاب لطفا بعد از مدت کوتاهی دوباره توکن رو همینجا بفرستین')
        return State.GITHUB_TOKEN

    if not result_boolean:
        update.message.reply_text(u'Wrong Token please retry!!')
        return State.GITHUB_TOKEN
    update.message.reply_text(u'عالی!! تایید شد')
    secret_obj.secret = update.message.text
    secret_obj.user_name = response
    secret_obj.save()
    update.message.reply_text(u'با تشکر از شما /start رو بزن')
    return ConversationHandler.END


def github_permission(bot, update, user_data):
    user = update.message.from_user
    secret_obj = Secret.get_or_none(id=user_data['last_secret'])

    if update.message.text == "YES":
        secret_obj.permitted = True
    else:
        secret_obj.permitted = False
    secret_obj.save()
    update.message.reply_text(u'با تشکر از شما /start رو بزن')

    return ConversationHandler.END


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(u'عه واا خدافظ برای شروع دوباره /start رو بزن ',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(bot=bot)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start, pass_user_data=True)],

        states={
            State.START: [RegexHandler('^(Github)$', github, pass_user_data=True),
                          RegexHandler('^(Secrets)$', secret)],

            State.GITHUB_SECRET: [RegexHandler('^(NewToken)$', github_get_secret_token, pass_user_data=True),
                                  RegexHandler('^(MyTokens)$', github_history_token, pass_user_data=True)

                                  ],
            State.GITHUB_HISTORY: [RegexHandler('^(\/\d*)$', github_delletin_from_history_token, pass_user_data=True)],
            State.GITHUB_LINK: [
                MessageHandler(Filters.text, get_github_link, pass_user_data=True, pass_job_queue=True)],
            State.GITHUB_TOKEN: [MessageHandler(Filters.text, github_access_auto_staring, pass_user_data=True)],

        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    if not os.path.isdir("db"):
        os.mkdir("db")
    main()
