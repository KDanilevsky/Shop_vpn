# --------------------------------------
# AMAZON
# secrets keep and load files:

# operator_encrypt.py
# secrets_schema.py
# cert_helper.py
# secrets_runtime.py
# example_usage.py
# IAM_KMS_policy_templates.py
# --------------------------------------
# GOOGLE

# operator_encrypt.py
# secrets_schema.py
# cert_helper.py
# secrets_runtime_gcp.py

# --------------------------------------


from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Float, ForeignKey, desc
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, LabeledPrice, Bot, helpers, LinkPreviewOptions, MessageEntity, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, PreCheckoutQueryHandler, ContextTypes, CallbackQueryHandler, Updater, ConversationHandler

from telegram.error import BadRequest
from dotenv import load_dotenv

import asyncio

from bitpapa_pay import BitpapaPay

import json
import jsonpickle

from flask import Flask, request, abort
from flask_talisman import Talisman


# from threading import Thread
import threading

from py3xui import Api, AsyncApi, Inbound, Client
import uuid

import qrcode
import time
from datetime import datetime, timedelta, timezone
from pytz import timezone as timezone_pytz

import schedule
# import aioschedule as schedule

import math

from operator import itemgetter
# пример работы с дэцимал - когда надо округлять в большую сторону.
# import decimal
# decimal.Decimal('8.333333').quantize(decimal.Decimal('.01'), rounding=decimal.ROUND_UP)
# Decimal('8.34')


MESSTOADM = 1
CHOOSEUSER = 2
TYPEUSERID = 3
CHOOSESERVER = 4
CHOOSEUSERBLO = 5
TYPEMESSALL = 6
GETINFO = 7
BLOCKID = 8
PLUSDAYSID = 9
PLUSDAYSDAYS = 10
PLUSDAYSSUB = 11
ADDPARTID = 12
ADDPARTPRC = 13
ADDPARTHTTP = 14
ADDPARTWLT = 15
PAYPARTID = 16
PAYPARTSUM = 17
UNBLOCKID = 18
# import certifi
# certifi.where()

# talisman vmesto sslify

# сначала pip install flask_sslify
# from flask_sslify import SSLify

# ------------------------загрузка переменных из дотэнв вирт окружения

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PAYMENT_PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
DATABASE_FILENAME = os.getenv('DATABASE_FILENAME')

TG_VPN_SHOP_BOT_ID = int(os.getenv('TG_VPN_SHOP_BOT_ID'))

FIRST_USER_IN_DB = int(os.getenv('FIRST_USER_IN_DB'))
BASE_PRICE_IN_USDT = float(os.getenv('BASE_PRICE_IN_USDT'))
BASE_PRICE_IN_RUB = float(os.getenv('BASE_PRICE_IN_RUB'))
DISCOUNT_BASE_PROCENTS = float(os.getenv('DISCOUNT_BASE_PROCENTS'))
DISCOUNT_BASE_PROCENTS_PROMO = float(os.getenv('DISCOUNT_BASE_PROCENTS_PROMO'))

VPNSERVER_COUNTRY_NO1 = os.getenv('VPNSERVER_COUNTRY_NO1')
VPNSERVER_HTTP_NO1 = os.getenv('VPNSERVER_HTTP_NO1')
VPNSERVER_USERNAME_NO1 = os.getenv('VPNSERVER_USERNAME_NO1')
VPNSERVER_PASS_NO1 = os.getenv('VPNSERVER_PASS_NO1')
VPNSERVER_TOKEN_NO1 = os.getenv('VPNSERVER_TOKEN_NO1')
PATH_TO_CUSTOM_SERT_NO1 = os.getenv('PATH_TO_CUSTOM_SERT_NO1')
VPN_SERVER_IP_NO1 = os.getenv('VPN_SERVER_IP_NO1')

MIN_PAY = float(os.getenv('MIN_PAY'))
MIN_PAY_RUB = float(os.getenv('MIN_PAY_RUB'))

UPDATED_PRICE = BASE_PRICE_IN_USDT

UPDATED_MIN_PAY = MIN_PAY

STANDART_PARTNER_PROCENT = float(os.getenv('STANDART_PARTNER_PROCENT'))
# ------------------------загрузка переменных из дотэнв вирт окружения END

# создадим лист со словарями для настроек серверов
# каждый элемент листа - сервер, айди листа == айди сервера. 



# -------------------------------------- MAKE dict for SERVERS VPN
# сюда лучше сразу писать макс сабскриптс - чтоб потом легко создавать записи в бд. - либо заявленную скорость, например.
# сервер рэйтинг заполняем - 0 для всех новых, 
# заполняем сервер фор блокед - 0 для всех, 1 - только для челов с заблоч сервера.

# country_id
# Germany - 1
# Netherlands - 2
# England - 3
# Canada - 4
# Argentina - 5
servers_list_of_dicts = []
servers_list_of_dicts.append({"server_id":0,"country":None,"country_id":0,"http":None,"ip":None,"username":None,"pass":None,"token":None,"sert":None,"max_users":0,"server_rating":0,"server_for_blocked":0,"blocked_rating":0})
servers_list_of_dicts.append({"server_id":1,"country":VPNSERVER_COUNTRY_NO1,"country_id":1,"http":VPNSERVER_HTTP_NO1,"ip":VPN_SERVER_IP_NO1,"username":VPNSERVER_USERNAME_NO1,"pass":VPNSERVER_PASS_NO1,"token":VPNSERVER_TOKEN_NO1,"sert":PATH_TO_CUSTOM_SERT_NO1,"max_users":20,"server_rating":0,"server_for_blocked":0,"blocked_rating":0})

BOT_SHOP_NAME = 'NoBordersShop'
BOT_TOP_IMAGE = 'vpn.jpg'

SERVER_COUNTRY_1 = 'Germany'
SERVER_COUNTRY_2 = 'Netherlands'
SERVER_COUNTRY_3 = 'England'
SERVER_COUNTRY_4 = 'Canada'
SERVER_COUNTRY_5 = 'Argentina'

SERVER_COUNTRY_ID_1 = 1
SERVER_COUNTRY_ID_2 = 2
SERVER_COUNTRY_ID_3 = 3
SERVER_COUNTRY_ID_4 = 4
SERVER_COUNTRY_ID_5 = 5

admins_list = []
admins_list.append(FIRST_USER_IN_DB)
# admins_list.append('12222211111')
print(admins_list)
# -------------------------------------- MAKE dict for SERVERS VPN END


# ----------------------------------------MAKE FLASK ASync for WEBHOOK
app = Flask(__name__)
# Talisman(app)
# sslify = SSLify(app)

@app.route('/webhook', methods = ['POST'])
async def webhook():
    if request.method == 'POST':
        
        print(request.json['secret_key'])
        if request.json['secret_key'] == 'blablabla123':
            print('webhook is ok')
            if request.json["status"] == 'paid':
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])
                # ищем сам инвойс в базе
                invoice = session.query(AllInvoices).filter_by(invoice_id=request.json['invoice_id']).first()
                invoice.invoice_status = 'paid'
                invoice.invoice_updated_at = subscription_start_new
                session.add(invoice)
                # session.commit()

                # в бд ищем кто оплатил по данному инвойсу - найдем айди пользователя
                # user_id_paid = session.query(AllInvoices.user_id).filter_by(invoice_id=request.json['invoice_id']).first()
                # user_id_paid = user_id_paid[0]
                user_id_paid = invoice.user_id
                
                # Сам оплативший пользователь
                user_paid = session.query(AllUsers).filter_by(user_id=user_id_paid).first()

                user_who_invited_id = user_paid.user_id_who_invited

                # Пригласивший пользователь
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()


                # проверка действует ли хоть одна подписка:
                
                


                # записываем транзакцию при поступлении на счет.
                if invoice.invoice_target == 'popolnenie_invoice_schet':
                    if user_who_invited.subscription_stop_id_1 is not None:
                        if subscription_start_new <= user_who_invited.subscription_stop_id_1:

                            user_who_invited.quantity_guests_paid += invoice.accounts_ammount
                            
                            session.add(user_who_invited)
                            # session.commit()
                        else:
                            user_who_invited.quantity_guests_paid_potent += invoice.accounts_ammount
                            
                            session.add(user_who_invited)
                            # session.commit()

                    transaction_db = AllTransactions(user_id=user_id_paid, trans_time=subscription_start_new, trans_ammount=invoice.invoice_ammount,trans_target=invoice.invoice_target, accounts_ammount=invoice.accounts_ammount, quantity_guests_paid=invoice.quantity_guests_paid,promo=invoice.promo )
                    session.add(transaction_db)
                    # session.commit()

                    # пополняем баланс
                    user_paid.user_balance += invoice.invoice_ammount
                    session.add(user_paid)
                    # session.commit()
                
                    # дальше создаем акк если его нет - зависит от аккаунтс аммаунт - если 3 - то 3 аккаунт айди у юзера проверяем - если 2 - то 2. Если акк айди пустой - подписки нет
                    # -значит создаем, если есть - тогда подписка есть и мы ее продляем.

                    


                    # И нужно наконец цельную функцию написать: 
                    # 1 - выбор сервера
                    # 2 - загрузка всех переменных для создания соединения с сервером
                    # 3 - создаем соединение
                    # 4 - грузим инбаундс лист
                    # 5 - делаем то, что должны: 
                    # а) создаем нового пользователя 
                    #  б) изменяем пользователя -т.е. продляем подписку
                    # 6 - возвращаем данные для подключения
                    # 7 - отправляем данные пользователю в виде строки и куар кода.
                    new_client_email = user_paid.user_name


                    # datetime_now = datetime.now()
                    # subscription_start_new = int(str(datetime_now.astimezone().timestamp()*1000)[:13])
                    time_delta = timedelta(days=30)
                    new_expiry_time = datetime_now + time_delta
                    new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
                    # subscription_start_new = int(str(datetime_now.astimezone().timestamp()*1000)[:13])
                    new_tg_id = user_paid.user_id
                    # add_client_to_3xui_server(new_client_email,new_expiry_time,new_tg_id)

                    # client = async_api.client.get_by_email(new_client_email)
                    # client_id = None
                    # for user_client in inbounds[0].settings.clients:
                    #     if user_client.email == user_email:
                    #         client_id = user_client.id
                    free_subs_in_mnth = user_paid.free_subs_given
                    sub_days = 30
                    if invoice.accounts_ammount == 1:
                        if user_paid.subscription_id_1 is not None:
                            subs_id = 1
                            # edit subscript
                            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        else:
                            subs_id = 1
                            # add new subscript
                            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string is not None and img_path is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                    if invoice.accounts_ammount == 2:
                        if user_paid.subscription_id_1 is not None:
                            subs_id = 1
                            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        else:
                            subs_id = 1
                            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string is not None and img_path is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        if user_paid.subscription_id_2 is not None:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        else:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_2 is not None and img_path_2 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                    if invoice.accounts_ammount == 3:
                        if user_paid.subscription_id_1 is not None:
                            subs_id = 1
                            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        else:
                            subs_id = 1
                            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string is not None and img_path is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        if user_paid.subscription_id_2 is not None:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        else:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_2 is not None and img_path_2 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        if user_paid.subscription_id_3 is not None:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                        else:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_3 is not None and img_path_3 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                    if invoice.accounts_ammount == 4:
                        if user_paid.subscription_id_1 is not None:
                            subs_id = 1
                            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        else:
                            subs_id = 1
                            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string is not None and img_path is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        if user_paid.subscription_id_2 is not None:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        else:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_2 is not None and img_path_2 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        if user_paid.subscription_id_3 is not None:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                        else:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_3 is not None and img_path_3 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                        if user_paid.subscription_id_4 is not None:
                            subs_id = 4
                            client_setttings_string_4, img_path_4 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_4, img_path_4)
                        else:
                            subs_id = 4
                            client_setttings_string_4, img_path_4 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_4 is not None and img_path_4 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_4, img_path_4)
                    if invoice.accounts_ammount == 5:
                        if user_paid.subscription_id_1 is not None:
                            subs_id = 1
                            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        else:
                            subs_id = 1
                            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string is not None and img_path is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                        if user_paid.subscription_id_2 is not None:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        else:
                            subs_id = 2
                            client_setttings_string_2, img_path_2 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_2 is not None and img_path_2 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_2, img_path_2)
                        if user_paid.subscription_id_3 is not None:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                        else:
                            subs_id = 3
                            client_setttings_string_3, img_path_3 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_3 is not None and img_path_3 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_3, img_path_3)
                        if user_paid.subscription_id_4 is not None:
                            subs_id = 4
                            client_setttings_string_4, img_path_4 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_4, img_path_4)
                        else:
                            subs_id = 4
                            client_setttings_string_4, img_path_4 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_4 is not None and img_path_4 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_4, img_path_4)
                        if user_paid.subscription_id_5 is not None:
                            subs_id = 5
                            client_setttings_string_5, img_path_5 = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, free_subs_in_mnth)
                            # await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_5, img_path_5)
                        else:
                            subs_id = 5
                            client_setttings_string_5, img_path_5 = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
                            if client_setttings_string_5 is not None and img_path_5 is not None:
                                await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string_5, img_path_5)

                    # списываем с баланса
                    # только сначала записываем транзакцию списания
                    transaction_db = AllTransactions(user_id=user_id_paid, trans_time=subscription_start_new, trans_ammount=invoice.invoice_ammount_fact,trans_target='spisanie_invoice_schet', accounts_ammount=invoice.accounts_ammount, quantity_guests_paid=invoice.quantity_guests_paid,promo=invoice.promo )
                    session.add(transaction_db)
                    # session.commit()

                    user_paid.user_balance -= invoice.invoice_ammount_fact
                    session.add(user_paid)
                    # session.commit()
                    
                    # Записываем партнеру выплаты за привлеченного чела.
                    if user_who_invited.is_partner == 1:
                        if user_who_invited.partner_procent:
                            procent_partnera = user_who_invited.partner_procent
                        else:
                            procent_partnera = STANDART_PARTNER_PROCENT
                        user_who_invited.total_earned += (invoice.invoice_ammount_fact * procent_partnera)/100
                        user_who_invited.last_mnth_total_earned += (invoice.invoice_ammount_fact * procent_partnera)/100
                        user_who_invited.balance_earner_fact += (invoice.invoice_ammount_fact * procent_partnera)/100


                        user_who_invited.balance_earner += (invoice.invoice_ammount_fact * procent_partnera)/100
                       
                    
                        session.add(user_who_invited)

                        transaction_part_db = PartnerTransactions(
                        user_id=user_who_invited.user_id,
                        trans_time=subscription_start_new,
                        trans_ammount=(invoice.invoice_ammount_fact * procent_partnera)/100,
                        trans_target='partner_popolnenie',
                        total_earned=user_who_invited.total_earned,
                        total_paid=user_who_invited.total_paid,
                        balance_earner=user_who_invited.balance_earner,
                        balance_earner_fact=user_who_invited.balance_earner_fact,
                        partner_wallet=user_who_invited.partner_wallet)
                    
                        session.add(transaction_part_db)
                        # session.commit()

                    # Записываем админу поступление средств
                    first_user_in_db_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).first()

                    first_user_in_db_db.last_mnth_total_earned += invoice.invoice_ammount_fact
                    first_user_in_db_db.total_earned += invoice.invoice_ammount_fact
                    first_user_in_db_db.balance_earner += invoice.invoice_ammount
                    first_user_in_db_db.balance_earner_fact += invoice.invoice_ammount_fact

                    session.add(first_user_in_db_db)

                    transaction_adm_db = PartnerTransactions(
                        user_id=FIRST_USER_IN_DB,
                        trans_time=subscription_start_new,
                        trans_ammount=invoice.invoice_ammount_fact,
                        trans_target='adm_popolnenie',
                        total_earned=first_user_in_db_db.total_earned,
                        total_paid=first_user_in_db_db.total_paid,
                        balance_earner=first_user_in_db_db.balance_earner,
                        balance_earner_fact=first_user_in_db_db.balance_earner_fact,
                        partner_wallet=first_user_in_db_db.partner_wallet)
                    
                    session.add(transaction_adm_db)
                    session.commit()

                    # мы пополняем на invoice_ammount, а списываем на invoice_ammount_fact

                # если пополняем баланс - то просто пишем в базу транзакцию, а затем пополняем баланс юзера на сумму.
                if invoice.invoice_target == 'popolnenie_balance':
                    transaction_db = AllTransactions(user_id=user_id_paid, trans_time=subscription_start_new, trans_ammount=invoice.invoice_ammount,trans_target=invoice.invoice_target, accounts_ammount=invoice.accounts_ammount, quantity_guests_paid=invoice.quantity_guests_paid,promo=invoice.promo )
                    session.add(transaction_db)
                    # session.commit()

                    # пополняем баланс
                    user_paid.user_balance += invoice.invoice_ammount
                    session.add(user_paid)
                    # session.commit()

                    # Записываем админу поступление средств
                    first_user_in_db_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).first()

                    first_user_in_db_db.balance_earner += invoice.invoice_ammount

                    session.add(first_user_in_db_db)

                    transaction_adm_db = PartnerTransactions(
                        user_id=FIRST_USER_IN_DB,
                        trans_time=subscription_start_new,
                        trans_ammount=invoice.invoice_ammount,
                        trans_target='adm_popolnenie',
                        total_earned=first_user_in_db_db.total_earned,
                        total_paid=first_user_in_db_db.total_paid,
                        balance_earner=first_user_in_db_db.balance_earner,
                        balance_earner_fact=first_user_in_db_db.balance_earner_fact,
                        partner_wallet=first_user_in_db_db.partner_wallet)
                    
                    session.add(transaction_adm_db)
                    session.commit()
                # if invoice.invoice_target == 'popolnenie_invoice_schet':
                #     pass
                # if invoice.invoice_target == 'popolnenie_balance':
                #     pass
                # дальше отдаем полученные настройки в сообщении
                # bot = Bot(token=TELEGRAM_TOKEN)
                # bot.send_message(chat_id=new_tg_id, text=client_setttings_string)
                # bot.send_photo(chat_id=new_tg_id, photo=open(img_path, 'rb'))
                # if os.path.exists(img_path):
                #     os.remove(img_path)
                return 'success', 200
            
    else:
        abort(400)


# ----------------------------------------MAKE FLASK ASync for WEBHOOK END


# ----------------------------------------MAKE TELEGRAM SEND FUNCS
async def tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path):
    bot = cont_bot
    await bot.send_message(chat_id=new_tg_id, text=client_setttings_string)
    await bot.send_photo(chat_id=new_tg_id, photo=open(img_path, 'rb'))
    if os.path.exists(img_path):
        os.remove(img_path)



async def send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=new_tg_id, text=client_setttings_string)
    await bot.send_photo(chat_id=new_tg_id, photo=open(img_path, 'rb'))
    if os.path.exists(img_path):
        os.remove(img_path)



async def send_message_to_user(new_tg_id, text, reply_markup=None):
    bot = Bot(token=TELEGRAM_TOKEN)
    if reply_markup:
        # await bot.send_message(chat_id=new_tg_id, text=text, reply_markup=reply_markup)
        await bot.send_photo(chat_id=new_tg_id, photo=open(f"{BOT_TOP_IMAGE}", 'rb'), caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        # await bot.send_message(chat_id=new_tg_id, text=text)
        await bot.send_photo(chat_id=new_tg_id, photo=open(f"{BOT_TOP_IMAGE}", 'rb'), caption=text, parse_mode="html")

# ----------------------------------------MAKE TELEGRAM SEND FUNCS END


# -----------------------------------------3XUI FUNCS to work with vpn servers

async def choose_server(server_country_id, server_add_rule):
    # Esli server_add_rule == 1 - to vibirautsa servera tolko s visokim ratingom, esli server_add_rule == 0, to vse krome serverov s visokim raitingom

    # выбор сервера - дописать алго
    servers = session.query(AllServers).all()

    min_servers_count_for_choose_rules = 5
    procent_servers_bez_dobavlenia = 20
    chosen_server = None

    servers_ratings_id_stack = []
    
    for server in servers:
        if server.country_id == server_country_id:
            di = {
                "id":server.id,
                "country_id":server.country_id,
                "rating":server.server_rating,
                "subs_count":server.all_subscriptions,
                "subs_max":server.max_subscriptions
                }
            servers_ratings_id_stack.append(di)
    # new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'), reverse=True)
    new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'))

    high_rate_serv_chosen = False
    for i in range(len(new_servers_ratings_id_stack)):
        if len(new_servers_ratings_id_stack) >= min_servers_count_for_choose_rules:
            count_servers_bez_dobavlenya = int((len(new_servers_ratings_id_stack) * procent_servers_bez_dobavlenia) / 100)
            if server_add_rule == 0:
                if i < len(new_servers_ratings_id_stack) - count_servers_bez_dobavlenya: # Esli nado vibrat serv kuda dobavlyaem tolko perenosom izza visokogo ratinga to stavim znak >=
                    if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
                        chosen_server = int(new_servers_ratings_id_stack[i]["id"])
            else:
                if i >= len(new_servers_ratings_id_stack) - count_servers_bez_dobavlenya:
                    if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
                        chosen_server = int(new_servers_ratings_id_stack[i]["id"])
                        high_rate_serv_chosen = True
        else:
            if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
                chosen_server = int(new_servers_ratings_id_stack[i]["id"])

    # ETO esli mi hotim dobavlyat po ratingu na drugie servera - kogda na servah s visokim ratingom net mesta
    # esli ne nado - prosto zakomentiruy - togda chosen_server = None
    if server_add_rule == 1:
        if len(new_servers_ratings_id_stack) >= min_servers_count_for_choose_rules:
            if high_rate_serv_chosen is False:
                new_servers_ratings_id_stack = sorted(servers_ratings_id_stack, key=itemgetter('rating'), reverse=True)
                for i in range(len(new_servers_ratings_id_stack)):
                    if new_servers_ratings_id_stack[i]["subs_count"] < new_servers_ratings_id_stack[i]["subs_max"]:
                        chosen_server = int(new_servers_ratings_id_stack[i]["id"])

    return chosen_server



async def add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, user_paid, subs_id):
    new_client_email = None
    new_expiry_time = None
    server_country_id = None
    if subs_id == 1:
        new_client_email = str(new_tg_id)+'-1'
        new_expiry_time = user_paid.subscription_stop_id_1
        server_country_id = 1
    if subs_id == 2:
        new_client_email = str(new_tg_id)+'-2'
        new_expiry_time = user_paid.subscription_stop_id_2
        server_country_id = 2
    if subs_id == 3:
        new_client_email = str(new_tg_id)+'-3'
        new_expiry_time = user_paid.subscription_stop_id_3
        server_country_id = 3
    if subs_id == 4:
        new_client_email = str(new_tg_id)+'-4'
        new_expiry_time = user_paid.subscription_stop_id_4
        server_country_id = 4
    if subs_id == 5:
        new_client_email = str(new_tg_id)+'-5'
        new_expiry_time = user_paid.subscription_stop_id_5
        server_country_id = 5

    servers = session.query(AllServers).all()
    max_subs = None
    total_subs = None
    for server in servers:
        if server.id == chosen_server:
            max_subs = server.max_subscriptions
            total_subs = server.all_subscriptions
            break

    if total_subs < max_subs:

    # chosen_server = None

    # chosen_server = choose_server(server_country_id, 0)

    # if chosen_server is not None:

        # мы хотим либо подписку добавлять - либо в бд в список вносить
        async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

        await async_api.login()
        vpn_ip = servers_list_of_dicts[chosen_server]['ip']
        # inbounds: list[Inbound] = async_api.inbound.get_list()

        # добавляем пользователя
        await add_client_to_3xui_server(async_api, new_client_email,new_expiry_time,new_tg_id)

        inbounds: list[Inbound] = await async_api.inbound.get_list()

        # subscription_id = None
        # for user_client in inbounds[0].settings.clients:
        #     if user_client.email == new_client_email:
        #         subscription_id = inbounds[0].settings.clients[0].id

        # после добавления клиента - нужно распихать все данные по таблицам в бд
        # время подписок - 1 2 3 4 5
        if subs_id == 1:
            # user_paid.subscription_id_1 = subscription_id
            user_paid.subscription_server_id_1 = chosen_server
            user_paid.subscription_autopay_id_1 = 1
            user_paid.subscription_stop_id_1 = new_expiry_time
            session.add(user_paid)
            session.commit()

            # session.query(AllUsers).filter_by(subscription_server_id_1=blocked_server_id).all()

            replaced_subs = session.query(ReplacedSubscriptions).filter_by(ReplacedSubscriptions.subscription_server_id_1.isnot(None), user_id=new_tg_id).first()
            replaced_subs.new_subscription_server_id_1 = chosen_server
            replaced_subs.replace_complited = 1
            session.add(replaced_subs)
            session.commit()

        if subs_id == 2:
            # user_paid.subscription_id_2 = subscription_id
            user_paid.subscription_server_id_2 = chosen_server
            user_paid.subscription_autopay_id_2 = 1
            user_paid.subscription_stop_id_2 = new_expiry_time
            session.add(user_paid)
            session.commit()

            replaced_subs = session.query(ReplacedSubscriptions).filter_by(ReplacedSubscriptions.subscription_server_id_2.isnot(None), user_id=new_tg_id).first()
            replaced_subs.new_subscription_server_id_2 = chosen_server
            replaced_subs.replace_complited = 1
            session.add(replaced_subs)
            session.commit()

        if subs_id == 3:
            # user_paid.subscription_id_3 = subscription_id
            user_paid.subscription_server_id_3 = chosen_server
            user_paid.subscription_autopay_id_3 = 1
            user_paid.subscription_stop_id_3 = new_expiry_time
            session.add(user_paid)
            session.commit()

            replaced_subs = session.query(ReplacedSubscriptions).filter_by(ReplacedSubscriptions.subscription_server_id_3.isnot(None), user_id=new_tg_id).first()
            replaced_subs.new_subscription_server_id_3 = chosen_server
            replaced_subs.replace_complited = 1
            session.add(replaced_subs)
            session.commit()

        if subs_id == 4:
            # user_paid.subscription_id_4 = subscription_id
            user_paid.subscription_server_id_4 = chosen_server
            user_paid.subscription_autopay_id_4 = 1
            user_paid.subscription_stop_id_4 = new_expiry_time
            session.add(user_paid)
            session.commit()

            replaced_subs = session.query(ReplacedSubscriptions).filter_by(ReplacedSubscriptions.subscription_server_id_4.isnot(None), user_id=new_tg_id).first()
            replaced_subs.new_subscription_server_id_4 = chosen_server
            replaced_subs.replace_complited = 1
            session.add(replaced_subs)
            session.commit()

        if subs_id == 5:
            # user_paid.subscription_id_5 = subscription_id
            user_paid.subscription_server_id_5 = chosen_server
            user_paid.subscription_autopay_id_5 = 1
            user_paid.subscription_stop_id_5 = new_expiry_time
            session.add(user_paid)
            session.commit()

            replaced_subs = session.query(ReplacedSubscriptions).filter_by(ReplacedSubscriptions.subscription_server_id_5.isnot(None), user_id=new_tg_id).first()
            replaced_subs.new_subscription_server_id_5 = chosen_server
            replaced_subs.replace_complited = 1
            session.add(replaced_subs)
            session.commit()

        # к нужному серверу приписать +1 подписку
        for server in servers:
            if server.id == chosen_server:
                server.all_subscriptions += 1
                session.add(server)
                session.commit()
        
        # replaced_subs = session.query(ReplacedSubscriptions).all()
        # replaced_subs.replace_complited = 1
        # session.add(replaced_subs)
        # session.commit()
    else:
        text_u = (
            f'Кончилось место на сервере id:{chosen_server}\n'
            # f'Закочились сервера с кантри id:{server_country_id}\n'
            
        )
        # keyboard = [
        #     [InlineKeyboardButton("Мои Аккаунты", callback_data="my_accounts")],
        # ]
        # reply_markup = InlineKeyboardMarkup(keyboard)
        await send_message_to_user(FIRST_USER_IN_DB, text_u)


async def add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days):
    # сначала выберем сервер
    # Нужно равномерно распределять нагрузку, при этом, чтобы кол-во клиентов не выходило за предел макс сабскриптионс.
    sub_d_1 = 0
    sub_d_2 = 0
    sub_d_3 = 0
    sub_d_4 = 0
    sub_d_5 = 0

    new_client_email = None
    server_country_id = None

    if subs_id == 1:
        # chosen_server = user_paid.subscription_server_id_1
        new_client_email = str(new_tg_id)+'-1'
        sub_d_1 = sub_days
        server_country_id = 1
    if subs_id == 2:
        # chosen_server = user_paid.subscription_server_id_2
        new_client_email = str(new_tg_id)+'-2'
        sub_d_2 = sub_days
        server_country_id = 2
    if subs_id == 3:
        # chosen_server = user_paid.subscription_server_id_3
        new_client_email = str(new_tg_id)+'-3'
        sub_d_3 = sub_days
        server_country_id = 3
    if subs_id == 4:
        # chosen_server = user_paid.subscription_server_id_4
        new_client_email = str(new_tg_id)+'-4'
        sub_d_4 = sub_days
        server_country_id = 4
    if subs_id == 5:
        # chosen_server = user_paid.subscription_server_id_5
        new_client_email = str(new_tg_id)+'-5'
        sub_d_5 = sub_days
        server_country_id = 5

    chosen_server = None

    chosen_server = choose_server(server_country_id, 0)


    # 123
    client_setttings_string = None
    img_path = None
    if chosen_server is None:
        # sub_asks = session.query(AllSubscriptionsAwaited).all()
        sub_asks = session.query(AllSubscriptionsAwaited).filter_by(user_id=new_tg_id).all()
        sub_ask_found = False
        for ask in sub_asks:
            if subs_id == 1:
                if ask.subscr_id_1 != 0:
                    sub_ask_found = True
            if subs_id == 2:
                if ask.subscr_id_2 != 0:
                    sub_ask_found = True
            if subs_id == 3:
                if ask.subscr_id_3 != 0:
                    sub_ask_found = True
            if subs_id == 4:
                if ask.subscr_id_4 != 0:
                    sub_ask_found = True
            if subs_id == 5:
                if ask.subscr_id_5 != 0:
                    sub_ask_found = True
            
        if sub_ask_found is False:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            subskr_ask = AllSubscriptionsAwaited(user_id=new_tg_id,ask_time=subscription_start_new, subscr_id_1=sub_d_1 ,subscr_id_2=sub_d_2 ,subscr_id_3=sub_d_3 ,subscr_id_4=sub_d_4,subscr_id_5=sub_d_5)
            session.add(subskr_ask)
            session.commit()

            text_u = (
                'Заявка на создание подписки принята.'
                'Новый сервер в стадии создания.'
                'Вы получите уведомление, как только сервер будет готов.'
                '(В течении 24 часов)'
            )
            text_a = (
                'Админ. Закончилось место на серверах.\n'
                'Срочно создай новые.\n'
            )
            await send_message_to_user(new_tg_id, text_u)
            await send_message_to_user(FIRST_USER_IN_DB, text_a)
    else:
        async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        # войдем на сервер
        # async_api = Api(host = VPNSERVER_HTTP_NO1, username = VPNSERVER_USERNAME_NO1, password = VPNSERVER_PASS_NO1, token = VPNSERVER_TOKEN_NO1, use_tls_verify =True, custom_certificate_path=PATH_TO_CUSTOM_SERT_NO1, logger=None)
        await async_api.login()
        vpn_ip = servers_list_of_dicts[chosen_server]['ip']
        # inbounds: list[Inbound] = async_api.inbound.get_list()

        # добавляем пользователя
        await add_client_to_3xui_server(async_api, new_client_email,new_expiry_time,new_tg_id)

        inbounds: list[Inbound] = await async_api.inbound.get_list()

        # subscription_id = None
        # for user_client in inbounds[0].settings.clients:
        #     if user_client.email == new_client_email:
        #         subscription_id = inbounds[0].settings.clients[0].id

        # после добавления клиента - нужно распихать все данные по таблицам в бд
        # время подписок - 1 2 3 4 5
        if subs_id == 1:
            # user_paid.subscription_id_1 = subscription_id
            user_paid.subscription_server_id_1 = chosen_server
            user_paid.subscription_autopay_id_1 = 1
            user_paid.subscription_stop_id_1 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 2:
            # user_paid.subscription_id_2 = subscription_id
            user_paid.subscription_server_id_2 = chosen_server
            user_paid.subscription_autopay_id_2 = 1
            user_paid.subscription_stop_id_2 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 3:
            # user_paid.subscription_id_3 = subscription_id
            user_paid.subscription_server_id_3 = chosen_server
            user_paid.subscription_autopay_id_3 = 1
            user_paid.subscription_stop_id_3 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 4:
            # user_paid.subscription_id_4 = subscription_id
            user_paid.subscription_server_id_4 = chosen_server
            user_paid.subscription_autopay_id_4 = 1
            user_paid.subscription_stop_id_4 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 5:
            # user_paid.subscription_id_5 = subscription_id
            user_paid.subscription_server_id_5 = chosen_server
            user_paid.subscription_autopay_id_5 = 1
            user_paid.subscription_stop_id_5 = new_expiry_time
            session.add(user_paid)
            session.commit()

        # к нужному серверу приписать +1 подписку
        for server in servers:
            if server.id == chosen_server:
                server.all_subscriptions += 1
                session.add(server)
                session.commit()
        

        # затем получим пользователя и составим строку настроек
        client_setttings_string, img_path = get_client_settings_string(inbounds, new_client_email, vpn_ip)

    return client_setttings_string, img_path

    # после отправки qr картинки пользователю - нужно ее удалять
async def plus_some_days_to_sub(servers_list_of_dicts, new_tg_id, subs_id, dayz):
    # servers = session.query(AllServers).all()

    user = session.query(AllUsers).filter_by(user_id=new_tg_id).first

    chosen_server = None
    if subs_id == 1:
        chosen_server = user.subscription_server_id_1
        new_client_email = str(new_tg_id)+'-1'
    if subs_id == 2:
        chosen_server = user.subscription_server_id_2
        new_client_email = str(new_tg_id)+'-2'
    if subs_id == 3:
        chosen_server = user.subscription_server_id_3
        new_client_email = str(new_tg_id)+'-3'
    if subs_id == 4:
        chosen_server = user.subscription_server_id_4
        new_client_email = str(new_tg_id)+'-4'
    if subs_id == 5:
        chosen_server = user.subscription_server_id_5
        new_client_email = str(new_tg_id)+'-5'

    async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
    await async_api.login()

    inbounds: list[Inbound] = await async_api.inbound.get_list()
    new_expiry_time = await update_existing_3xui_client(async_api, inbounds, new_client_email, dayz)

    if subs_id == 1:
        user.subscription_stop_id_1 = new_expiry_time
        session.add(user)
        session.commit()

    if subs_id == 2:
        user.subscription_stop_id_2 = new_expiry_time
        session.add(user)
        session.commit()

    if subs_id == 3:
        user.subscription_stop_id_3 = new_expiry_time
        session.add(user)
        session.commit()

    if subs_id == 4:
        user.subscription_stop_id_4 = new_expiry_time
        session.add(user)
        session.commit()

    if subs_id == 5:
        user.subscription_stop_id_5 = new_expiry_time
        session.add(user)
        session.commit()

async def edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, new_tg_id, user_paid, subs_id, subs_id_not_prodlyaem):
    # сначала определим на каком сервере подписка
    chosen_server = None
    if subs_id == 1:
        chosen_server = user_paid.subscription_server_id_1
        new_client_email = str(new_tg_id)+'-1'
    if subs_id == 2:
        chosen_server = user_paid.subscription_server_id_2
        new_client_email = str(new_tg_id)+'-2'
    if subs_id == 3:
        chosen_server = user_paid.subscription_server_id_3
        new_client_email = str(new_tg_id)+'-3'
    if subs_id == 4:
        chosen_server = user_paid.subscription_server_id_4
        new_client_email = str(new_tg_id)+'-4'
    if subs_id == 5:
        chosen_server = user_paid.subscription_server_id_5
        new_client_email = str(new_tg_id)+'-5'
    
    # if chosen_server is not None:

    client_setttings_string, img_path = None

    if subs_id > subs_id_not_prodlyaem:
        async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
        await async_api.login()

        # add_client_to_3xui_server(new_client_email,new_expiry_time,new_tg_id)
        inbounds: list[Inbound] = await async_api.inbound.get_list()
        new_expiry_time = await update_existing_3xui_client(async_api, inbounds, new_client_email, 30)

        # inbounds: list[Inbound] = async_api.inbound.get_list()

        # subscription_id = None
        # for user_client in inbounds[0].settings.clients:
        #     if user_client.email == new_client_email:
        #         subscription_id = inbounds[0].settings.clients[0].id

        if subs_id == 1:
            user_paid.subscription_stop_id_1 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 2:
            user_paid.subscription_stop_id_2 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 3:
            user_paid.subscription_stop_id_3 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 4:
            user_paid.subscription_stop_id_4 = new_expiry_time
            session.add(user_paid)
            session.commit()

        if subs_id == 5:
            user_paid.subscription_stop_id_5 = new_expiry_time
            session.add(user_paid)
            session.commit()

        vpn_ip = servers_list_of_dicts[chosen_server]['ip']
        client_setttings_string, img_path = get_client_settings_string(inbounds, new_client_email, vpn_ip)

    return client_setttings_string, img_path

async def autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem):
    chosen_server = None
    new_client_email = None
    user_sub_id = None
    if subs_id == 1:
        chosen_server = user.subscription_server_id_1
        new_client_email = str(new_tg_id)+'-1'
        user_sub_id = user.subscription_id_1
    if subs_id == 2:
        chosen_server = user.subscription_server_id_2
        new_client_email = str(new_tg_id)+'-2'
        user_sub_id = user.subscription_id_2
    if subs_id == 3:
        chosen_server = user.subscription_server_id_3
        new_client_email = str(new_tg_id)+'-3'
        user_sub_id = user.subscription_id_3
    if subs_id == 4:
        chosen_server = user.subscription_server_id_4
        new_client_email = str(new_tg_id)+'-4'
        user_sub_id = user.subscription_id_4
    if subs_id == 5:
        chosen_server = user.subscription_server_id_5
        new_client_email = str(new_tg_id)+'-5'
        user_sub_id = user.subscription_id_5

    if user_sub_id is not None:

        if subs_id > subs_id_not_prodlyaem:
            # chosen_server = user_sub_server_id
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()

            client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, user.user_id, user, subs_id)

            # списываем с баланса, записываем транзакцию.
            # отправляем сообщение, что подписка номер subs_id продлена успешно
            # await send_user_settings_string_and_qr_code_then_del_qr(user.user_id, client_setttings_string, img_path)
    else:
        # тут надо выбрать свободный серв
        # chosen_server = user_sub_server_id
        if subs_id > subs_id_not_prodlyaem:
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()

            # # subs_id = 1
            # new_client_email = str(user.user_id)+'-'+str(subs_id)
            # client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, user.user_id, user, subs_id)
            
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            time_delta = timedelta(days=30)
            new_expiry_time = datetime_now + time_delta
            new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
            new_tg_id = user.user_id
            sub_days=30
            client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user, subs_id, sub_days)
            # await send_user_settings_string_and_qr_code_then_del_qr(user.user_id, client_setttings_string, img_path)

# Отправим базу данных админу с выбором сервера
async def export_db_to_admin_from_server(servers_list_of_dicts, server_id):
    #  Для этого в настройках панели должен быть прописан телеграм айди админа и подключен телеграм бот для пересылки. Отдельный.?
    async_api = AsyncApi(host = servers_list_of_dicts[server_id]['http'], username = servers_list_of_dicts[server_id]['username'], password = servers_list_of_dicts[server_id]['pass'], token = servers_list_of_dicts[server_id]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[server_id]['sert'], logger=None)
    await async_api.login()
    await async_api.database.export()

async def export_tg_vpn_shop_db_to_admin():
    bot = Bot(token=TELEGRAM_TOKEN)
    chat_id = FIRST_USER_IN_DB
    with open(DATABASE_FILENAME, "rb") as f:
        await bot.send_document(chat_id, f)

# тут нужно добавлять в бд сервера, если их еще там нет.
# for server in servers_list_of_dicts:

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# в начале - проходим весь лист - и если нет такого айди - создаем запись в таблице

# f = open(PATH_TO_CUSTOM_SERT_NO1, "r")
# print(f.read())



# async_api = Api(host = VPNSERVER_HTTP_NO1, username = VPNSERVER_USERNAME_NO1, password = VPNSERVER_PASS_NO1, token = VPNSERVER_TOKEN_NO1, use_tls_verify =True, custom_certificate_path=PATH_TO_CUSTOM_SERT_NO1, logger=None)
# print(async_api)
# async_api.login()
# inbounds: list[Inbound] = async_api.inbound.get_list()
# print(inbounds)
# print('--------------------------------')
# print(type(inbounds[0]))
# print(inbounds[0])
# print(inbounds[0].port)
# print(inbounds[0].protocol)
# print(inbounds[0].settings)
# print('--------------------------------')
# print(inbounds[0].settings.clients)
# print('--------------------------------')
# print(inbounds[0].settings.clients[0])
# print('--------------------------------')
# print(inbounds[0].settings.clients[0].email)
# print(inbounds[0].stream_settings.network)
# print(inbounds[0].stream_settings.reality_settings['settings']['publicKey'])
# print(inbounds[0].stream_settings.reality_settings['serverNames'][0])
# print(inbounds[0].stream_settings.reality_settings['shortIds'][0])
# print('===================================')
# client: Client = async_api.client.get_by_email("y6ng9kkw")
# print(client)
# print('--------------------------------')


# pbk = inbounds[0].stream_settings.reality_settings['settings']['publicKey']
# fp = inbounds[0].stream_settings.reality_settings['settings']['fingerprint']
# sni = inbounds[0].stream_settings.reality_settings['serverNames'][0]
# sid = inbounds[0].stream_settings.reality_settings['shortIds'][0]
# client_setttings_string = f'{inbounds[0].protocol}://{inbounds[0].settings.clients[0].id}@{VPN_SERVER_IP_NO1}:{inbounds[0].port}?type={inbounds[0].stream_settings.network}&security={inbounds[0].stream_settings.security}&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F&flow={inbounds[0].settings.clients[0].flow}#{inbounds[0].settings.clients[0].email}'
# print(client_setttings_string)
# vpn_ip = VPN_SERVER_IP_NO1
# Получение ссылки ключа и Создание Qr кода с настройками
def get_client_settings_string(inbounds, user_email, vpn_ip):

    client_setttings_string = None
    usr_list_id = 0
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            pbk = inbounds[0].stream_settings.reality_settings['settings']['publicKey']
            fp = inbounds[0].stream_settings.reality_settings['settings']['fingerprint']
            sni = inbounds[0].stream_settings.reality_settings['serverNames'][0]
            sid = inbounds[0].stream_settings.reality_settings['shortIds'][0]
            # client_setttings_string = f'{inbounds[0].protocol}://{inbounds[0].settings.clients[0].id}@{vpn_ip}:{inbounds[0].port}?type={inbounds[0].stream_settings.network}&security={inbounds[0].stream_settings.security}&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F&flow={inbounds[0].settings.clients[0].flow}#{inbounds[0].settings.clients[0].email}'
            client_setttings_string = f'{inbounds[0].protocol}://{inbounds[0].settings.clients[usr_list_id].id}@{vpn_ip}:{inbounds[0].port}?type={inbounds[0].stream_settings.network}&security={inbounds[0].stream_settings.security}&pbk={pbk}&fp={fp}&sni={sni}&sid={sid}&spx=%2F&flow={inbounds[0].settings.clients[usr_list_id].flow}#{inbounds[0].settings.clients[usr_list_id].email}'
        usr_list_id += 1

    img = qrcode.make(client_setttings_string)
    type(img)  # qrcode.image.pil.PilImage
    img_path = f"{user_email}.png"
    img.save(img_path) # Тут по идее имэйл потом будет - а в нем .ком или .ру - может файл потом не сохраняться

    return client_setttings_string, img_path

# print(get_client_settings_string(inbounds, 'gxfe89v5', vpn_ip))

# Затем дожна быть отправка настроек клиенту и удаление куар

# Добавление нового клиента
async def add_client_to_3xui_server(async_api, new_client_email,new_expiry_time,new_tg_id):
    flow = "xtls-rprx-vision"
    new_client = await Client(id=str(uuid.uuid4()), email=new_client_email,expiry_time=new_expiry_time,tg_id=new_tg_id,flow=flow, enable=True)
    inbound_id = 1

    await async_api.client.add(inbound_id, [new_client])

# Обновление времени подписки клиента
async def update_existing_3xui_client(async_api, inbounds, user_email, dayz):
    client = await async_api.client.get_by_email(user_email)

    # находим new_expiry_time
    time_now = int(str(time.time()*1000)[:13])
    if time_now > client.expiry_time:
        datetime_now = datetime.now(timezone.utc)
        time_delta = timedelta(days=dayz)
        new_expiry_time = datetime_now + time_delta
        new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
    else:
        new_expiry_time = int(((client.expiry_time/1000) + (dayz*24*60*60))*1000)

    client.expiry_time = new_expiry_time
    flow = "xtls-rprx-vision"

    client_id = None
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            client_id = user_client.id
    # print(client_id)
    # print(type(client_id))
    if client_id is not None:
        client.id = client_id
        await async_api.client.update(client.id, client, flow=flow)

    return new_expiry_time

# удаление всех неактивных клиентов
async def delete_depleted_clients(async_api, inbound):
    inbound_id = 1
    await async_api.client.delete_depleted(inbound_id) # inbound.id

async def delete_client(async_api, tg_id, suff):
    user_email = str(tg_id)+f'-{suff}'
    client = async_api.client.get_by_email(user_email)
    inbound_id = 1

    inbounds: list[Inbound] = async_api.inbound.get_list()
    client_id = None
    for user_client in inbounds[0].settings.clients:
        if user_client.email == user_email:
            client_id = user_client.id
    # print(client_id)
    # print(type(client_id))
    if client_id is not None:
        client.id = client_id
    # print(client.id)
    async_api.client.delete(inbound_id, client.id)
# user_email = 'y6ng9kkw'

# client = async_api.client.get_by_email(user_email)
# client.email = "y6ng7kkw"
# async_api.client.update(client.id, client)


# update_existing_3xui_client(inbounds, user_email)


# по дате - сначала проверка подписки
# если подписка не истекла - то прибавляем 30 дней к expiry_time
# если подписка истекла - то прибавляем 30 дней к текущему времени
# expiry_time=1732933818441
#  1731724862
# time_now = time.time()
# datetime_now = datetime.now()
# time_delta = timedelta(days=30)
# print(time_now)
# print(datetime_now)
# print(time_delta)
# # print(time_now + time_delta)
# new_expiry_time = datetime_now + time_delta
# print(datetime_now + time_delta)
# new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])
# print(new_expiry_time)
# newt = ((1732933818441/1000) + (30*24*60*60))*1000
# print(newt)
# newt = 
# exp_time_current = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime(1732933818441/1000))
# new_expiry_time = exp_time_current + time_delta
# new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])
# # Создание Qr кода с настройками
# def make_client_settings_qr_code(client_setttings_string):
#     img = qrcode.make(client_setttings_string)
#     type(img)  # qrcode.image.pil.PilImage
#     img.save("test_qr.png")





# async def get_inbound_list(async_api):
# # Some examples of using the API.
#     inbounds: list[Inbound] = await async_api.inbound.get_list()
#     print(inbounds)
# await get_inbound_list(async_api)



# -----------------------------------------3XUI FUNCS to work with vpn servers END


# -----------------------------------------MAKE DATABASE FOR TELEGRAM SHOP SERVER
Base = declarative_base()



engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()


class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)


class CartItem(Base):
    __tablename__ = 'cart_items'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    quantity = Column(Integer, default=1)
    item = relationship("Item")



class ActiveUsers(Base):
    __tablename__ = 'active_users'
    id = Column(Integer, primary_key=True)

class InactiveUsers(Base):
    __tablename__ = 'inactive_users'
    id = Column(Integer, primary_key=True)

class AllUsers(Base):
    __tablename__ = 'all_users'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    user_name = Column(String, unique=True, nullable=False)
    user_full_name = Column(String, unique=False, nullable=True)

    user_id_who_invited = Column(BigInteger, nullable=False)
    quantity_guests_paid = Column(Integer, nullable=False)
    quantity_guests_paid_potent = Column(Integer, nullable=False)
    free_subs_given = Column(Integer, unique=False, nullable=False)
    # subscription_id_1 = Column(String, unique=True, nullable=True)

    subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
    subscription_autopay_id_1 = Column(Integer, unique=False, nullable=True)
    subscription_stop_id_1 = Column(Integer, unique=False, nullable=True)
    # subscription_id_2 = Column(String, unique=True, nullable=True)

    subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
    subscription_autopay_id_2 = Column(Integer, unique=False, nullable=True)
    subscription_stop_id_2 = Column(Integer, unique=False, nullable=True)
    # subscription_id_3 = Column(String, unique=True, nullable=True)

    subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
    subscription_autopay_id_3 = Column(Integer, unique=False, nullable=True)
    subscription_stop_id_3 = Column(Integer, unique=False, nullable=True)
    # subscription_id_4 = Column(String, unique=True, nullable=True)

    subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
    subscription_autopay_id_4 = Column(Integer, unique=False, nullable=True)
    subscription_stop_id_4 = Column(Integer, unique=False, nullable=True)
    # subscription_id_5 = Column(String, unique=True, nullable=True)

    subscription_server_id_5 = Column(Integer, unique=False, nullable=True)
    subscription_autopay_id_5 = Column(Integer, unique=False, nullable=True)
    subscription_stop_id_5 = Column(Integer, unique=False, nullable=True)

    # invites_1 = Column(String, unique=False, nullable=True)
    # invites_2 = Column(String, unique=False, nullable=True)
    # invites_3 = Column(String, unique=False, nullable=True)
    # invites_4 = Column(String, unique=False, nullable=True)
    # invites_5 = Column(String, unique=False, nullable=True)

    user_promo_new = Column(Integer, nullable=True)
    user_promo_new_days = Column(Integer, nullable=True)

    user_time_rating = Column(Integer, unique=False, nullable=True) # сюда пишем каждую оплату подписки.
    user_server_rating = Column(Integer, unique=False, nullable=True) # сюда пишем если чувак был на заблоченном сервере клиентом
    user_blocked = Column(Integer, unique=False, nullable=True)

    user_balance = Column(Float, unique=False, nullable=True)

    is_partner = Column(Integer, unique=False, nullable=True, default=0)
    partner_procent = Column(Float, unique=False, nullable=True, default=0)
    partner_http = Column(String, unique=False, nullable=True)
    partner_wallet = Column(String, unique=True, nullable=True)

    last_mnth_total_earned = Column(Float, unique=False, nullable=True, default=0)
    last_mnth_total_paid = Column(Float, unique=False, nullable=True, default=0)

    total_earned = Column(Float, unique=False, nullable=True, default=0)
    total_paid = Column(Float, unique=False, nullable=True, default=0)
    last_pay = Column(Float, unique=False, nullable=True, default=0)

    balance_earner = Column(Float, unique=False, nullable=True, default=0)
    balance_earner_fact = Column(Float, unique=False, nullable=True, default=0)

    asked_redirect = Column(Integer, unique=False, nullable=True)
    asked_redirect_yes = Column(Integer, unique=False, nullable=True)
    asked_time = Column(Integer, unique=False, nullable=True)
    # last_invoice_id = Column(String, unique=True, nullable=True) # нужен он тут вообще? Если есть отдельная таблица с инвойсами. (отд таблицу сделал из-за того, что чел может несколько инвойсов выставить по ошибке, а потом оплатить - не обязательно последний.)

class AdminStats(Base):
    __tablename__ = 'admin_stats'
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    prev_mnth_earned = Column(Float, unique=False, nullable=True)
    mnth_earned = Column(Float, unique=False, nullable=True)
    prev_total_earned = Column(Float, unique=False, nullable=True)
    total_earned = Column(Float, unique=False, nullable=True)

    prev_mnth_earned_fact = Column(Float, unique=False, nullable=True)
    mnth_earned_fact = Column(Float, unique=False, nullable=True)
    prev_total_earned_fact = Column(Float, unique=False, nullable=True)
    total_earned_fact = Column(Float, unique=False, nullable=True)

class AllInvoices(Base):
    __tablename__ = 'all_invoices'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    user_name = Column(String, unique=False, nullable=False)
    user_full_name = Column(String, unique=False, nullable=True)
    invoice_id = Column(String, unique=True, nullable=False)
    invoice_curency = Column(String, unique=False, nullable=False)
    accounts_ammount = Column(Integer, unique=False, nullable=False)
    invoice_ammount = Column(Float, unique=False, nullable=False)
    invoice_ammount_fact = Column(Float, unique=False, nullable=False)
    invoice_status = Column(String, unique=False, nullable=False)
    invoice_created_at = Column(String, unique=False, nullable=False)
    invoice_updated_at = Column(String, unique=False, nullable=False)
    invoice_target = Column(String, unique=False, nullable=False)
    quantity_guests_paid = Column(Integer, nullable=False)
    promo = Column(Integer, unique=False, nullable=True)
    invoice_url = Column(String, unique=True, nullable=False)

class AllServers(Base):
    __tablename__ = 'all_servers'
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, unique=True, nullable=False)
    country = Column(String, unique=False, nullable=True)
    country_id = Column(Integer, unique=False, nullable=False)
    max_subscriptions = Column(Integer, unique=False, nullable=False)
    all_subscriptions = Column(Integer, unique=False, nullable=True)
    active_subscriptions = Column(Integer, unique=False, nullable=True)
    server_rating = Column(Float, unique=False, nullable=False) # расчитываем раз в сутки на основе рейтинга челиков на серве и общего кол-ва.
    server_for_blocked = Column(Integer, unique=False, nullable=False) # если 1 - то, серв для юзверей с заблоч серва, если 0 - то для всех
    blocked_rating =Column(Float, unique=False, nullable=False)

class AllTransactions(Base):
    __tablename__ = 'all_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    trans_time = Column(String, unique=False, nullable=False)
    trans_ammount = Column(Float, unique=False, nullable=False)
    # trans_curency = Column(String, unique=False, nullable=False)
    trans_target = Column(String, unique=False, nullable=False)
    accounts_ammount = Column(Integer, unique=False, nullable=True)
    quantity_guests_paid = Column(Integer, nullable=False)
    promo = Column(Integer, unique=False, nullable=True)
# 123

class PartnerTransactions(Base):
    __tablename__ = 'partner_transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    trans_time = Column(String, unique=False, nullable=False)
    trans_ammount = Column(Float, unique=False, nullable=False)
    # trans_curency = Column(String, unique=False, nullable=False)
    trans_target = Column(String, unique=False, nullable=False)
    total_earned = Column(Float, unique=False, nullable=True)
    total_paid = Column(Float, unique=False, nullable=True)
    balance_earner = Column(Float, unique=False, nullable=True)
    balance_earner_fact = Column(Float, unique=False, nullable=True)
    partner_wallet = Column(String, unique=True, nullable=True)

class AllSubscriptionsAwaited(Base):
    __tablename__ = 'all_subscriptions_awaited'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    ask_time = Column(String, unique=False, nullable=False)
    subscr_id_1 = Column(Integer, unique=False, nullable=True) # по умолчанию 0 - если не 0, а число - то выдаем подписку - число - кол-во дней.
    subscr_id_2 = Column(Integer, unique=False, nullable=True)
    subscr_id_3 = Column(Integer, unique=False, nullable=True)
    subscr_id_4 = Column(Integer, unique=False, nullable=True)
    subscr_id_5 = Column(Integer, unique=False, nullable=True)

class ReplacedSubscriptions(Base):
    __tablename__ = 'replaced_subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    user_time_rating = Column(Integer, unique=False, nullable=True) # сюда пишем каждую оплату подписки.
    user_server_rating = Column(Integer, unique=False, nullable=True) # сюда пишем если чувак был на заблоченном сервере клиентом
    user_blocked = Column(Integer, unique=False, nullable=True)
    replace_time = Column(String, unique=False, nullable=False)
    replace_complited = Column(Integer, unique=False, nullable=True)

    subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_5 = Column(Integer, unique=False, nullable=True)

    new_subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_5 = Column(Integer, unique=False, nullable=True)

class ReplaceAsks(Base):
    __tablename__ = 'replace_asks'
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    user_time_rating = Column(Integer, unique=False, nullable=True) # сюда пишем каждую оплату подписки.
    user_server_rating = Column(Integer, unique=False, nullable=True) # сюда пишем если чувак был на заблоченном сервере клиентом
    user_blocked = Column(Integer, unique=False, nullable=True)
    replace_time = Column(String, unique=False, nullable=False)
    replace_complited = Column(Integer, unique=False, nullable=True)

    subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
    subscription_server_id_5 = Column(Integer, unique=False, nullable=True)

    new_subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
    new_subscription_server_id_5 = Column(Integer, unique=False, nullable=True)

    asked_redirect_yes = Column(Integer, unique=False, nullable=True)

class FunctionsResultsTime(Base):
    __tablename__ = 'functions_results_time'
    id = Column(Integer, primary_key=True)
    function_name = Column(String, unique=False, nullable=False)
    function_time = Column(String, unique=False, nullable=False, default='1900-01-01 00:00:00.000000')

Base.metadata.create_all(engine)

# -----------------------------------------MAKE DATABASE FOR TELEGRAM SHOP SERVER END
# # Создаем новый товар
# new_item = Item(name="Sample Item", price=19.99)
# session.add(new_item)
# session.commit()
# # Проверяем, добавился ли товар
# item = session.query(Item).filter_by(name="Sample Item").first()
# print(item.name, item.price)


# -------------------------------------------------------MAKE FUNKS TO PAY FROM BITPAPA
# bitpapa pay 
async def confirm_top_up_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
    promo = user_db.user_promo_new
    quant = user_db.quantity_guests_paid
    
    # subscript_stop_1 = user_db.subscription_stop_id_1
    # subscript_stop_2 = user_db.subscription_stop_id_2
    # subscript_stop_3 = user_db.subscription_stop_id_3
    # subscript_stop_4 = user_db.subscription_stop_id_4
    # subscript_stop_5 = user_db.subscription_stop_id_5

    # subs_stop_list = []
    # subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    # subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    # subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    # subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    # subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    # datetime_now = datetime.now()
    # datetime_now_int = int(str(datetime_now.astimezone().timestamp()*1000)[:13])

    # for subs in subs_stop_list:
    #     if subs["subscript_time"] is not None:
    #         if subs["subscript_time"] >= datetime_now_int:
    #             acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10]))
    #             delta_ostatok = acc_time - datetime_now
    #             subs["subscript_delta"] = delta_ostatok.days
    #         else:
    #             subs["subscript_delta"] = 0
    #     else:
    #             subs["subscript_delta"] = 0

    # delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    # delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    # delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    # delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    # delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]

    accounts_amount = 0

    make_invoice = True
    # if accounts_amount == 1:
    #     if delta_ostatok_1 <= 15:
    #         make_invoice = True
    # if accounts_amount == 2:
    #     if delta_ostatok_2 <= 15:
    #         make_invoice = True
    # if accounts_amount == 3:
    #     if delta_ostatok_3 <= 15:
    #         make_invoice = True
    # if accounts_amount == 4:
    #     if delta_ostatok_4 <= 15:
    #         make_invoice = True
    # if accounts_amount == 5:
    #     if delta_ostatok_5 <= 15:
    #         make_invoice = True

    # проверка на бан юзера
    if user_db.user_blocked == 1:
        make_invoice = False

    if make_invoice is True:
        bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=update.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]
        
        # print(quantity_guests_paid)
        
        # if quantity_guests_paid is not None:
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT

        final_price = context.user_data['balance_top_up']
        
        # print(context.user_data['counted_price_last'])
        result = await bitpapa_pay.create_invoice("USDT", final_price)
        print(result.model_dump())
        print(
            result.invoice.id,
            result.invoice.currency_code,
            result.invoice.amount,
            result.invoice.status,
            result.invoice.created_at,
            result.invoice.updated_at,
            result.invoice.url
        )
        json_string = jsonpickle.encode(result)
        await bitpapa_pay.close()
        # print(update.message.from_user.name)
        # print(update.from_user.name)
        invoice_db = AllInvoices(user_id=update.from_user.id, user_name=update.from_user.name, user_full_name=update.from_user.full_name,invoice_id=result.invoice.id,invoice_curency=result.invoice.currency_code,accounts_ammount=accounts_amount,invoice_ammount=result.invoice.amount,invoice_ammount_fact=result.invoice.amount, invoice_status=result.invoice.status,invoice_created_at=result.invoice.created_at,invoice_updated_at=result.invoice.updated_at,invoice_target='popolnenie_balance', promo = promo, quantity_guests_paid=quant, invoice_url=result.invoice.url)
        session.add(invoice_db)
        session.commit()
        keyboard = [
            [InlineKeyboardButton("Оплатить", url=result.invoice.url)],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            f"Пополнение Баланса на {final_price} $\n"
            f"{result.invoice.url} \n"
        )
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("Выбрать доп аккаунт \U0001F4B5", callback_data="count")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "Невозможно пополнить баланс.\n"
        )
        await update.message.reply_text(text, reply_markup=reply_markup)

        

async def bitpappa_create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
    promo = user_db.user_promo_new
    quant = user_db.quantity_guests_paid

    subscript_stop_1 = user_db.subscription_stop_id_1
    subscript_stop_2 = user_db.subscription_stop_id_2
    subscript_stop_3 = user_db.subscription_stop_id_3
    subscript_stop_4 = user_db.subscription_stop_id_4
    subscript_stop_5 = user_db.subscription_stop_id_5

    subs_stop_list = []
    subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    for subs in subs_stop_list:
        if subs["subscript_time"] is not None:
            if subs["subscript_time"] >= datetime_now_int:
                acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
                delta_ostatok = acc_time - datetime_now
                subs["subscript_delta"] = delta_ostatok.days
            else:
                subs["subscript_delta"] = 0
        else:
                subs["subscript_delta"] = 0

    delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]

    accounts_amount = context.user_data['accounts_amount']

    make_invoice = False
    if accounts_amount == 1:
        if delta_ostatok_1 <= 15:
            make_invoice = True
    if accounts_amount == 2:
        if delta_ostatok_2 <= 15:
            make_invoice = True
    if accounts_amount == 3:
        if delta_ostatok_3 <= 15:
            make_invoice = True
    if accounts_amount == 4:
        if delta_ostatok_4 <= 15:
            make_invoice = True
    if accounts_amount == 5:
        if delta_ostatok_5 <= 15:
            make_invoice = True

    # проверка на бан
    if user_db.user_blocked == 1:
        make_invoice = False

    if make_invoice is True:
        bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)



        price = context.user_data['counted_price_last']
        final_price = None
        inv_price = None
        if price < UPDATED_MIN_PAY:
            final_price = UPDATED_MIN_PAY
            inv_price = price
        else:
            final_price = price
            inv_price = price
        print(final_price)
 
        result = await bitpapa_pay.create_invoice("USDT", final_price)
        print(result.model_dump())
        print(
            result.invoice.id,
            result.invoice.currency_code,
            result.invoice.amount,
            result.invoice.status,
            result.invoice.created_at,
            result.invoice.updated_at,
            result.invoice.url
        )
        json_string = jsonpickle.encode(result)
        await bitpapa_pay.close()
        invoice_db = AllInvoices(user_id=update.from_user.id, user_name=update.from_user.name, user_full_name=update.from_user.full_name,invoice_id=result.invoice.id,invoice_curency=result.invoice.currency_code,accounts_ammount=accounts_amount,invoice_ammount=result.invoice.amount,invoice_ammount_fact=inv_price,invoice_status=result.invoice.status,invoice_created_at=result.invoice.created_at,invoice_updated_at=result.invoice.updated_at,invoice_target='popolnenie_invoice_schet', promo = promo, quantity_guests_paid=quant, invoice_url=result.invoice.url)
        session.add(invoice_db)
        session.commit()
        keyboard = [
            [InlineKeyboardButton("Оплатить", url=result.invoice.url)],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            f"Подписка {BOT_SHOP_NAME}: 30 дней \n"
            f"Количество аккаунтов: {context.user_data['accounts_amount']}\n"
            f"Стоимость: {context.user_data['counted_price_last']} $\n"
            f"Скидка на акк.: {context.user_data['quantity_guests_paid_last'] * DISCOUNT_BASE_PROCENTS} %\n\n"
            "Скидка начисляется последовательно: \n"
            "До 100% - на 1-й акк, свыше - на 2-й, и т.д.\n"
            f"{result.invoice.url} \n"
        )
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        keyboard = [
            [InlineKeyboardButton("Выбрать доп аккаунт \U0001F4B5", callback_data="count")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "Невозможно продлить подписку.\n"
            "Т.к. продление возможно, если осталось меньше 15 дней.\n"
        )
        await update.message.reply_text(text, reply_markup=reply_markup)


async def bitpappa_get_invoices():
    bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)
    result = await bitpapa_pay.get_invoices()
    for invoice in result.invoices:
        print(
            invoice.id,
            invoice.currency_code,
            invoice.amount,
            invoice.status,
            invoice.created_at,
            invoice.updated_at,
            invoice.url
        )
    json_string = jsonpickle.encode(result)
    await bitpapa_pay.close()
    # print(json_string)
    return result
    # await update.message.reply_text(json_string)


# НЕДОПИСАНО!
async def apeal_account_didnt_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_now = datetime.now(timezone.utc)
    days_to_lookback = 7
    invoices_asked = await bitpappa_get_invoices()
    all_user_invoices = session.query(AllInvoices).filter_by(user_id=update.from_user.id).all()
    invoices_in_lookback = []
    for user_invoice in all_user_invoices:
        # user_invoice.invoice_created_at
        invoice_created_time = datetime.fromisoformat(user_invoice.invoice_created_at).astimezone(tz=timezone.utc)
        invoice_created_time = format(invoice_created_time.strftime('%Y-%m-%d %H:%M:%S'))
        invoice_created_time = datetime.strptime(invoice_created_time, '%Y-%m-%d %H:%M:%S').astimezone(tz=timezone.utc)
        
        if (time_now - invoice_created_time).days <= days_to_lookback:
            invoices_in_lookback.append(user_invoice)
            print((time_now - invoice_created_time).days)
            print(user_invoice.invoice_created_at)
    for invoice_asked in invoices_asked:
        for invoice_in_lookback in invoices_in_lookback:
            if invoice_in_lookback.invoice_id == invoice_asked.invoice_id:
                if invoice_asked.invoice_status == 'paid':
                    # выдаем подписку. (продляем)
                    # записываем в базу, что инвойс оплачен
                    pass



# async def bitpappa_get_exchange_rates_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
async def bitpappa_get_exchange_rates_all():
    bitpapa_pay = BitpapaPay(api_token=PAYMENT_PROVIDER_TOKEN)
    result = await bitpapa_pay.get_exchange_rates_all()
    await bitpapa_pay.close()
    # print(result)
    # print('--------------------------------')
    # print(result.rates['USDT_RUB'])
    json_string = jsonpickle.encode(result)


    # await bitpapa_pay.close()
    # print(json_string)
    # print('--------------------------------')
    # print(json_string[0])
    # print(json_string[1])
    # print(json_string[2])

    # print(json_string)
    # await update.message.reply_text(json_string)
    usdt_rub_course = None
    try:
        usdt_rub_course = float(result.rates['USDT_RUB'])
    except:
        usdt_rub_course = None
    return usdt_rub_course
    # await update.message.reply_text(result.rates['USDT_RUB'])

async def auto_price_with_course():
    usdt_rub_course = await bitpappa_get_exchange_rates_all()
    global UPDATED_PRICE
    global UPDATED_MIN_PAY
    if usdt_rub_course:
        if BASE_PRICE_IN_USDT * usdt_rub_course < BASE_PRICE_IN_RUB:
            UPDATED_PRICE = math.ceil((BASE_PRICE_IN_RUB/usdt_rub_course)*100)/100
        else:
            UPDATED_PRICE = BASE_PRICE_IN_USDT

        if MIN_PAY * usdt_rub_course < MIN_PAY_RUB:
            UPDATED_MIN_PAY = math.ceil((MIN_PAY_RUB/usdt_rub_course)*100)/100
        else:
            UPDATED_MIN_PAY = MIN_PAY

    print('Updated_price: '+str(UPDATED_PRICE))
    return UPDATED_PRICE, UPDATED_MIN_PAY

# print()

# -------------------------------------------------------MAKE FUNKS TO PAY FROM BITPAPA END
# telegram bot shop

# privetstvie

# -------------------------------------------------------TELEGRAM SHOP BOT
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # """Send a deep-linked URL when the command /start is issued."""
    user_id = None
    if update.message.from_user.id == TG_VPN_SHOP_BOT_ID:
        user_id = update.from_user.id
        user_full_name = update.from_user.full_name
    else:
        user_id = update.message.from_user.id
        user_full_name = update.message.from_user.full_name

    # Тут сразу будем добавлять пользователя перешедшего, если его id еще нет в базе.
    user_in_db = session.query(AllUsers).filter_by(user_id=update.message.from_user.id).all()
    print(update.message.from_user.id)
    print(user_in_db)
    if not user_in_db:
        if context.args:
            # 
            print(context.args[0])
            print(type(context.args[0]))
            inviter_id = None
            try:
                inviter_id = int(context.args[0])
            except (TypeError, ValueError):
                inviter_id = None
            # if isinstance(inviter_id, int):
            if inviter_id:
                user_in_db_inv = session.query(AllUsers).filter_by(user_id=inviter_id).all()
                blocked_u = user_in_db_inv.user_blocked
                if user_in_db_inv and blocked_u != 1:
                    # Тут новому юзеру выдаем промо аккаунт
                    # Но сначала должен быть выбор сервера - подключение к нему.
                    # if db_user.user_promo_free == 1:

                        # new_client_email = update.message.from_user.name

                    datetime_now = datetime.now(timezone.utc)
                    time_delta = timedelta(days=5)
                    new_expiry_time = datetime_now + time_delta
                    new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
                    subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])
                    new_tg_id = update.message.from_user.id

                    new_client_email = str(new_tg_id)+'-1'
                        # add_client_to_3xui_server(new_client_email,new_expiry_time,new_tg_id)

                        # client = async_api.client.get_by_email(new_client_email)
                        # client_id = None
                        # for user_client in inbounds[0].settings.clients:
                        #     if user_client.email == user_email:
                        #         client_id = user_client.id
                    db_user = AllUsers(user_id=update.message.from_user.id, user_name=update.message.from_user.name, user_full_name=update.message.from_user.full_name, user_id_who_invited=context.args[0], quantity_guests_paid=0,quantity_guests_paid_potent=0, free_subs_given=0,subscription_autopay_id_1=0,subscription_autopay_id_2=0,subscription_autopay_id_3=0,subscription_autopay_id_4=0,subscription_autopay_id_5=0, user_promo_new=1, user_promo_new_days=new_expiry_time, user_time_rating=0,user_server_rating=0,user_blocked=0,user_balance=0)
                    # db_user = AllUsers(user_id=update.message.from_user.id, user_name=update.message.from_user.name, user_full_name=update.message.from_user.full_name,user_id_who_invited=context.args[0],quantity_guests_paid=0,user_promo_free=1,subscription_start_id_1=subscription_start_new,subscription_stop_id_1=new_expiry_time)
                    session.add(db_user)
                    session.commit()
    # !!!!!!!!!!!
                    subs_id = 1
                    sub_days = 5
                    client_setttings_string, img_path = await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time, new_tg_id, db_user, subs_id, sub_days)
                    print(client_setttings_string)
                    if client_setttings_string is not None and img_path is not None:
                        await send_user_settings_string_and_qr_code_then_del_qr(new_tg_id, client_setttings_string, img_path)
                else:
                    print("inviter is not valid")
            else:
                print("not invited")

    bot = context.bot
    cont = str(update.message.from_user.id)
    cont2 = update.message.from_user.full_name
    cont3 = update.message.from_user.name # Телеграм айди нэйм @
    # print(update.message.from_user.name)
    argss = context.args 
    url = helpers.create_deep_linked_url(bot.username, str(cont), group=False)
    text = (
        f"{user_full_name}, Добро пожаловать в {BOT_SHOP_NAME} - Интеренет без границ.\n\n\n"
        # "/count - Расчитать индивидуальную стоимость на 30 дней\n\n" # В каунт будет расчет - вывод цены - выставить счет
        # "/free - Использовать сервис полностью Бесплатно\n\n"
        # "/pluses - Преимущества сервиса\n\n"
        # "/settings - Настройка iphone, android, pc\n\n"
        # "/ref - Реферальная сылка\n\n"
        # "/usl - Условия использования\n\n"
        # "/ref - Поделиться бесплатным промо с другом на 5 дней\n\n"
        # "/help - Меню помощи\n\n"
    )
    # text6 = f"Поделиться бесплатным промо периодом с другом на 5 дней:\n\n {url} \n"

    # keyboard = InlineKeyboardMarkup.from_button(
    #     InlineKeyboardButton(text="Перейти", callback_data="help")
    # )
    if  update.message.from_user.id  in admins_list or update.from_user.id  in admins_list:
        keyboard = [
            # [
            #     InlineKeyboardButton("Option 1", callback_data="1"),
            #     InlineKeyboardButton("Option 2", callback_data="2"),
            # ],
            
            [InlineKeyboardButton("Мои Аккаунты", callback_data="my_accounts")],
            [InlineKeyboardButton("Пополнить баланс", callback_data="balance_top_up")],
            [InlineKeyboardButton("Автопродление", callback_data="auto_pay_subs")],
            [InlineKeyboardButton("Расчитать стоимость на 30 дней \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Использовать сервис Бесплатно \U0001F525", callback_data="free")],
            [InlineKeyboardButton("Преимущества сервиса \U0001F4A5", callback_data="pluses")],
            [InlineKeyboardButton("Настройка iphone, android, pc \U0001F4F1", callback_data="settings")],
            [InlineKeyboardButton("Реферальная сылка \U0001F381", callback_data="ref")],
            [InlineKeyboardButton("Условия использования \U0001F4DD", callback_data="usl")],
            [InlineKeyboardButton("Инструкция по оплате \U0001F4D6", callback_data="pay_help")],
            [InlineKeyboardButton("Отправить сообщение админу", callback_data="call_adm")],
            [InlineKeyboardButton("Отправить ответ от админа", callback_data="admin_reply")],
            [InlineKeyboardButton("Объявление Администратора", callback_data="admin_send_all")],
            [InlineKeyboardButton("Отметить юзеров на заблок сервере", callback_data="admin_mark_all_users_on_server")],
            [InlineKeyboardButton("Добавить дней к подписке", callback_data="adm_plus_usr_days")],
            [InlineKeyboardButton("Узнать инфо юзера", callback_data="adm_user_info")],
            [InlineKeyboardButton("Заблокировать юзера", callback_data="adm_block_user")],
            [InlineKeyboardButton("Разблокировать юзера", callback_data="adm_unblock_user")],
            
            [InlineKeyboardButton("Инфо", callback_data="adm_part_info")],
            [InlineKeyboardButton("Добавить партнера", callback_data="adm_add_partner")],
            [InlineKeyboardButton("Показать всех партнеров", callback_data="adm_show_partners")],
            [InlineKeyboardButton("Выплатить партнеру", callback_data="adm_pay_partner")],
            # [InlineKeyboardButton("Помощь", callback_data="help")],
            # [InlineKeyboardButton("", callback_data="bitpappa_get_exchange_rates_all")],
            [InlineKeyboardButton("Аккаунт не оплатился", callback_data="apeal_account_didnt_paid")],
            
        ]
    else:
        keyboard = [
            # [
            #     InlineKeyboardButton("Option 1", callback_data="1"),
            #     InlineKeyboardButton("Option 2", callback_data="2"),
            # ],
            
            [InlineKeyboardButton("Мои Аккаунты", callback_data="my_accounts")],
            [InlineKeyboardButton("Пополнить баланс", callback_data="balance_top_up")],
            [InlineKeyboardButton("Автопродление", callback_data="auto_pay_subs")],
            [InlineKeyboardButton("Расчитать стоимость на 30 дней \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Использовать сервис Бесплатно \U0001F525", callback_data="free")],
            [InlineKeyboardButton("Преимущества сервиса \U0001F4A5", callback_data="pluses")],
            [InlineKeyboardButton("Настройка iphone, android, pc \U0001F4F1", callback_data="settings")],
            [InlineKeyboardButton("Реферальная сылка \U0001F381", callback_data="ref")],
            [InlineKeyboardButton("Условия использования \U0001F4DD", callback_data="usl")],
            [InlineKeyboardButton("Инструкция по оплате \U0001F4D6", callback_data="pay_help")],
            [InlineKeyboardButton("Отправить сообщение админу", callback_data="call_adm")],

            [InlineKeyboardButton("Инфо", callback_data="adm_part_info")],
            # [InlineKeyboardButton("Помощь", callback_data="help")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)


    # await update.message.reply_text(f'{text}', reply_markup=reply_markup) # в argss будет айди реферала
    try:
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    except BadRequest:
        # mess_idss = []
        # mess_idss.append(update.message.message_id)
        # mess_idss.append(update.message.message_id - 1)
        # mess_idss.append(update.message.message_id - 2)
        # mess_idss.append(update.message.message_id - 3)
        # mess_idss.append(update.message.message_id - 4)
        # print(mess_idss)
        # await bot.delete_messages(message_ids=mess_idss, chat_id=user_id)

        await bot.send_photo(chat_id=user_id, photo=open(f"{BOT_TOP_IMAGE}", 'rb'), caption=text, reply_markup=reply_markup, parse_mode="html")



async def count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    
    # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=update.from_user.id).first()
    # quantity_guests_paid = quantity_guests_paid[0]


    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    balance_all = user_db.user_balance

    quantity_guests_paid = int(user_db.quantity_guests_paid)

    user_promo = user_db.user_promo_new
    user_promo_days = user_db.user_promo_new_days

    subscript_stop_1 = user_db.subscription_stop_id_1
    subscript_stop_2 = user_db.subscription_stop_id_2
    subscript_stop_3 = user_db.subscription_stop_id_3
    subscript_stop_4 = user_db.subscription_stop_id_4
    subscript_stop_5 = user_db.subscription_stop_id_5

    subs_stop_list = []
    subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    for subs in subs_stop_list:
        if subs["subscript_time"] is not None:
            if subs["subscript_time"] >= datetime_now_int:
                acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
                delta_ostatok = acc_time - datetime_now
                subs["subscript_delta"] = delta_ostatok.days
            else:
                subs["subscript_delta"] = 0
        else:
                subs["subscript_delta"] = 0

    delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]

    if user_db.user_blocked != 1:
    # text = (
    #         f"{update.from_user.full_name},\n"
    #         f"<b>Аккаунт 1:</b> Осталось: {delta_ostatok_1} дней\n"
    #         f"<b>Аккаунт 2:</b> Осталось: {delta_ostatok_2} дней\n"
    #         f"<b>Аккаунт 3:</b> Осталось: {delta_ostatok_3} дней\n"
    #         f"<b>Аккаунт 4:</b> Осталось: {delta_ostatok_4} дней\n"
    #         f"<b>Аккаунт 5:</b> Осталось: {delta_ostatok_5} дней\n"
    #     )

        if user_promo == 1:
            datetime_now = datetime.now(timezone.utc)
            datetime_now = int(str(datetime_now.timestamp()*1000)[:13])
            if datetime_now > user_promo_days:
                user_promo = 0
                user_db.user_promo_new = 0

                session.add(user_db)
                session.commit()
    
        
        if quantity_guests_paid is not None:
            # quantity_guests_paid = int(quantity_guests_paid)
            
            counted_price = math.ceil((UPDATED_PRICE * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100))*100)/100
            if counted_price < 0:
                counted_price = 0
        else:
            counted_price = UPDATED_PRICE

        quantity_guests_paid_last = quantity_guests_paid
        accounts_for_free = 0

        if user_promo == 1:
            counted_price_last = math.ceil(((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100)*100)/100

            all_accounts_to_buy = 1

            text = (
                f"{update.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:


            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 1
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{update.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2}", callback_data="subscript_2")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3}", callback_data="subscript_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await update.message.reply_text(f'{text}', reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
    # quantity_guests_paid = quantity_guests_paid[0]

    user_db = session.query(AllUsers).filter_by(user_id=query.from_user.id).first()
    quantity_guests_paid = int(user_db.quantity_guests_paid)

    balance_all = user_db.user_balance

    user_blocked = user_db.user_blocked
    user_promo = user_db.user_promo_new
    user_promo_days = user_db.user_promo_new_days

    subscript_stop_1 = user_db.subscription_stop_id_1
    subscript_stop_2 = user_db.subscription_stop_id_2
    subscript_stop_3 = user_db.subscription_stop_id_3
    subscript_stop_4 = user_db.subscription_stop_id_4
    subscript_stop_5 = user_db.subscription_stop_id_5

    subs_stop_list = []
    subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    subsc_auto_pay_1 = None
    subsc_auto_pay_2 = None
    subsc_auto_pay_3 = None
    subsc_auto_pay_4 = None
    subsc_auto_pay_5 = None
    if user_db.subscription_autopay_id_1 == 0:
        subsc_auto_pay_1 = 'Отключен'
    else:
        subsc_auto_pay_1 = 'Включен'
    if user_db.subscription_autopay_id_2 == 0:
        subsc_auto_pay_2 = 'Отключен'
    else:
        subsc_auto_pay_2 = 'Включен'
    if user_db.subscription_autopay_id_3 == 0:
        subsc_auto_pay_3 = 'Отключен'
    else:
        subsc_auto_pay_3 = 'Включен'
    if user_db.subscription_autopay_id_4 == 0:
        subsc_auto_pay_4 = 'Отключен'
    else:
        subsc_auto_pay_4 = 'Включен'
    if user_db.subscription_autopay_id_5 == 0:
        subsc_auto_pay_5 = 'Отключен'
    else:
        subsc_auto_pay_5 = 'Включен'

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    for subs in subs_stop_list:
        if subs["subscript_time"] is not None:
            if subs["subscript_time"] >= datetime_now_int:
                acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
                delta_ostatok = acc_time - datetime_now
                subs["subscript_delta"] = delta_ostatok.days
            else:
                subs["subscript_delta"] = 0
        else:
                subs["subscript_delta"] = 0

    delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]
    # text = (
    #         f"{update.from_user.full_name},\n"
    #         f"<b>Аккаунт 1:</b> Осталось: {delta_ostatok_1} дней\n"
    #         f"<b>Аккаунт 2:</b> Осталось: {delta_ostatok_2} дней\n"
    #         f"<b>Аккаунт 3:</b> Осталось: {delta_ostatok_3} дней\n"
    #         f"<b>Аккаунт 4:</b> Осталось: {delta_ostatok_4} дней\n"
    #         f"<b>Аккаунт 5:</b> Осталось: {delta_ostatok_5} дней\n"
    #     )
    if user_promo == 1:
        datetime_now = datetime.now(timezone.utc)
        datetime_now = int(str(datetime_now.timestamp()*1000)[:13])
        if datetime_now > user_promo_days:
            user_promo = 0
            user_db.user_promo_new = 0

            session.add(user_db)
            session.commit()

    if user_promo == 0:
        pass

    
    if quantity_guests_paid is not None:
        quantity_guests_paid = int(quantity_guests_paid) # >=1 and < 20, ==20, >=21 and <30, 30, >=31 and <40, 40, >=41 and <50, >=50+
        counted_price = math.ceil((UPDATED_PRICE * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100))*100)/100 #при 20 получаем прайс 0!
        if counted_price < 0:
            counted_price = 0
    else:
        counted_price = UPDATED_PRICE

    if query.data == 'start' and user_blocked != 1:
        await start(query, context)
    # if query.data == 'help':
    #     await help_command(query, context)
    if query.data == 'count' and user_blocked != 1:
        await count(query, context)
    if query.data == 'free' and user_blocked != 1:
        await free(query, context)
    if query.data == 'pluses' and user_blocked != 1:
        await pluses(query, context)
    if query.data == 'settings' and user_blocked != 1:
        await settings(query, context)
    if query.data == 'pay_help' and user_blocked != 1:
        await pay_help(query, context)
    if query.data == 'ref' and user_blocked != 1:
        await referal_link(query, context)
    if query.data == 'usl' and user_blocked != 1:
        await usloviya(query, context)
    if query.data == 'create_invoice' and user_blocked != 1:
        await bitpappa_create_invoice(query, context)

    if query.data == 'call_adm':
        await call_adm(query, context)
    if query.data == 'admin_reply' and user_blocked != 1:
        await admin_reply(query, context)
    
    if query.data == 'admin_send_all' and user_blocked != 1:
        await admin_send_all(query, context)
    
    if query.data == 'adm_user_info' and user_blocked != 1:
        await adm_user_info(query, context)
    if query.data == 'adm_block_user' and user_blocked != 1:
        await adm_block_user(query, context)
    if query.data == 'adm_unblock_user' and user_blocked != 1:
        await adm_unblock_user(query, context)

    if query.data == 'admin_mark_all_users_on_server' and user_blocked != 1:
        await admin_mark_all_users_on_server(query, context)

    if query.data == 'adm_plus_usr_days' and user_blocked != 1:
        await adm_plus_usr_days(query, context)

    
    if query.data == 'adm_part_info' and user_blocked != 1:
        await adm_part_info(query, context)
    
    if query.data == 'adm_add_partner' and user_blocked != 1:
        await adm_add_partner(query, context)
    
    if query.data == 'adm_show_partners' and user_blocked != 1:
        await adm_show_partners(query, context)
    
    if query.data == 'adm_pay_partner' and user_blocked != 1:
        await adm_pay_partner(query, context)



    if query.data == 'auto_pay_subs' and user_blocked != 1:
        await auto_pay_subs(query, context)


    if query.data == 'balance_top_up' and user_blocked != 1:
        await balance_top_up(query, context)


    if query.data == 'ask_confirm' and user_blocked != 1:
        await ask_confirm(query, context)

    # if query.data == 'ask_confirm_2':
    #     await ask_confirm_2(query, context)

    # if query.data == 'ask_confirm_3':
    #     await ask_confirm_3(query, context)

    # if query.data == 'ask_confirm_4':
    #     await ask_confirm_4(query, context)

    # if query.data == 'ask_confirm_5':
    #     await ask_confirm_5(query, context)
    # if query.data == 'bitpappa_get_exchange_rates_all' and user_blocked != 1:
    #     await bitpappa_get_exchange_rates_all(query, context)
    if query.data == 'apeal_account_didnt_paid' and user_blocked != 1:
        await apeal_account_didnt_paid(query, context)
    

    if query.data == 'my_accounts' and user_blocked != 1:
        await my_accounts(query, context)

    if query.data == 'subscript_1_get_info' and user_blocked != 1:
        await subscript_1_get_info(query, context)
    
    if query.data == 'subscript_2_get_info' and user_blocked != 1:
        await subscript_2_get_info(query, context)
    
    if query.data == 'subscript_3_get_info' and user_blocked != 1:
        await subscript_3_get_info(query, context)

    if query.data == 'subscript_4_get_info' and user_blocked != 1:
        await subscript_4_get_info(query, context)

    if query.data == 'subscript_5_get_info' and user_blocked != 1:
        await subscript_5_get_info(query, context)

    if query.data == 'balance_top_up_1' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $ \u2714", callback_data="balance_top_up_1_ch")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 10.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_1_ch' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"
            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 0.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await query.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        # await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_2' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $ \u2714", callback_data="balance_top_up_2_ch")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 15.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_2_ch' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 0.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_3' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $ \u2714", callback_data="balance_top_up_3_ch")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 20.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_3_ch' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 0.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_4' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $ \u2714", callback_data="balance_top_up_4_ch")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 25.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_4_ch' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 0.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_5' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $ \u2714", callback_data="balance_top_up_5_ch")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 30.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'balance_top_up_5_ch' and user_blocked != 1:
        text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

            )
        keyboard = [
            [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
            [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
            [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
            [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
            [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
            [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['balance_top_up'] = 0.0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'confirm_top_up_balance' and user_blocked != 1:
        await confirm_top_up_balance(query, context)

    if query.data == 'auto_pay_1' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж", callback_data="auto_pay_2")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 1
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    
    if query.data == 'auto_pay_1_ch' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж", callback_data="auto_pay_1")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж", callback_data="auto_pay_2")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 0
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    
    if query.data == 'auto_pay_2' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 2
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_2_ch' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж", callback_data="auto_pay_2")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 1
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_3' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж \u2714", callback_data="auto_pay_3_ch")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 3
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_3_ch' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 2
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_4' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж \u2714", callback_data="auto_pay_3_ch")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж \u2714", callback_data="auto_pay_4_ch")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 4
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_4_ch' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж \u2714", callback_data="auto_pay_3_ch")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 3
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_5' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж \u2714", callback_data="auto_pay_3_ch")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж \u2714", callback_data="auto_pay_4_ch")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж \u2714", callback_data="auto_pay_5_ch")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 5
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'auto_pay_5_ch' and user_blocked != 1:
        text = (
            f"{query.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж \u2714", callback_data="auto_pay_1_ch")],
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж \u2714", callback_data="auto_pay_2_ch")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж \u2714", callback_data="auto_pay_3_ch")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж \u2714", callback_data="auto_pay_4_ch")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
            [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        context.user_data['accounts_autopay'] = 4
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'confirm_auto_pay' and user_blocked != 1:
        autopay_accs = context.user_data['accounts_autopay']
        # user_db = session.query(AllUsers).filter_by(user_id=query.from_user.id).first()

        if autopay_accs == 0:
            user_db.subscription_autopay_id_1 = 0
            user_db.subscription_autopay_id_2 = 0
            user_db.subscription_autopay_id_3 = 0
            user_db.subscription_autopay_id_4 = 0
            user_db.subscription_autopay_id_5 = 0
            session.add(user_db)
            session.commit()

        if autopay_accs == 1:
            user_db.subscription_autopay_id_1 = 1
            user_db.subscription_autopay_id_2 = 0
            user_db.subscription_autopay_id_3 = 0
            user_db.subscription_autopay_id_4 = 0
            user_db.subscription_autopay_id_5 = 0
            session.add(user_db)
            session.commit()

        if autopay_accs == 2:
            user_db.subscription_autopay_id_1 = 1
            user_db.subscription_autopay_id_2 = 1
            user_db.subscription_autopay_id_3 = 0
            user_db.subscription_autopay_id_4 = 0
            user_db.subscription_autopay_id_5 = 0
            session.add(user_db)
            session.commit()

        if autopay_accs == 3:
            user_db.subscription_autopay_id_1 = 1
            user_db.subscription_autopay_id_2 = 1
            user_db.subscription_autopay_id_3 = 1
            user_db.subscription_autopay_id_4 = 0
            user_db.subscription_autopay_id_5 = 0
            session.add(user_db)
            session.commit()

        if autopay_accs == 4:
            user_db.subscription_autopay_id_1 = 1
            user_db.subscription_autopay_id_2 = 1
            user_db.subscription_autopay_id_3 = 1
            user_db.subscription_autopay_id_4 = 1
            user_db.subscription_autopay_id_5 = 0
            session.add(user_db)
            session.commit()

        if autopay_accs == 5:
            user_db.subscription_autopay_id_1 = 1
            user_db.subscription_autopay_id_2 = 1
            user_db.subscription_autopay_id_3 = 1
            user_db.subscription_autopay_id_4 = 1
            user_db.subscription_autopay_id_5 = 1
            session.add(user_db)
            session.commit()
        
        text =(
            'Количество аккаунтов для автопродления изменено.'
        )
        keyboard = [
            [InlineKeyboardButton("Автопродление", callback_data="auto_pay_subs")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_2' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3}", callback_data="subscript_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)


        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 1
        # counted_price_last = counted_price * 2
        accounts_for_free = 0

        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 2)*100)/100

            all_accounts_to_buy = 2

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

                )
            
        
        else:
            
            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 2
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 2
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_2_checked' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2}", callback_data="subscript_2")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3}", callback_data="subscript_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid
        # counted_price_last = counted_price
        accounts_for_free = 0

        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100))*100)/100

            all_accounts_to_buy = 1

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:


            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 1
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )

        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_3' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} \u2714", callback_data="subscript_3_checked")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 2
        # counted_price_last = counted_price * 3
        accounts_for_free = 0
        
        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 3)*100)/100

            all_accounts_to_buy = 3

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:

            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 3
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 3
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_3_checked' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3}", callback_data="subscript_3")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 1
        # counted_price_last = counted_price * 2
        accounts_for_free = 0
        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 2)*100)/100

            all_accounts_to_buy = 2

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:

            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 2
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 2
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_4' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} \u2714", callback_data="subscript_3_checked")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} \u2714", callback_data="subscript_4_checked")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 3
        # counted_price_last = counted_price * 4
        accounts_for_free = 0

        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 4)*100)/100

            all_accounts_to_buy = 4

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:
        
            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 4
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 4
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_4_checked' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} \u2714", callback_data="subscript_3_checked")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4}", callback_data="subscript_4")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 2
        # counted_price_last = counted_price * 3
        accounts_for_free = 0
      
        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 3)*100)/100   

            all_accounts_to_buy = 3

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:

            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 3
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100 

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 3
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_5' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} \u2714", callback_data="subscript_3_checked")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} \u2714", callback_data="subscript_4_checked")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} \u2714", callback_data="subscript_5_checked")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 4
        # counted_price_last = counted_price * 5
        accounts_for_free = 0
       
        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 5)*100)/100   

            all_accounts_to_buy = 5

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:

            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 5
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1

            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100   

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                # f"{query.from_user.name}"
            )
        # accounts_amount = 5
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    if query.data == 'subscript_5_checked' and user_blocked != 1:
        keyboard = [
            [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} \u2714", callback_data="subscript_2_checked")],
            [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} \u2714", callback_data="subscript_3_checked")],
            [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} \u2714", callback_data="subscript_4_checked")],
            [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5}", callback_data="subscript_5")],
            [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
            [InlineKeyboardButton("Назад", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await query.edit_message_reply_markup(reply_markup=reply_markup)

        # quantity_guests_paid = session.query(AllUsers.quantity_guests_paid).filter_by(user_id=query.from_user.id).first()
        # quantity_guests_paid = quantity_guests_paid[0]

        
        # if quantity_guests_paid is not None:
        #     quantity_guests_paid = int(quantity_guests_paid)
        #     counted_price = BASE_PRICE_IN_USDT * ((100 - (quantity_guests_paid * DISCOUNT_BASE_PROCENTS))/100)
        #     if counted_price < 0:
        #         counted_price = 0
        # else:
        #     counted_price = BASE_PRICE_IN_USDT
        quantity_guests_paid_last = quantity_guests_paid + 3
       
        accounts_for_free = 0
        if user_promo == 1:
            counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * 4)*100)/100  

            all_accounts_to_buy = 4

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в течении промо-периода составляет:</b>  {DISCOUNT_BASE_PROCENTS_PROMO} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Бесплатные аккаунты не доступны во время промо-периода.</b> \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"

            )
            
        
        else:
        
            if quantity_guests_paid >= 20 * 5:
                accounts_for_free = 5
            if quantity_guests_paid >= 20 * 4 and quantity_guests_paid < 20 * 5:
                accounts_for_free = 4
            if quantity_guests_paid >= 20 * 3 and quantity_guests_paid < 20 * 4:
                accounts_for_free = 3
            if quantity_guests_paid >= 20 * 2 and quantity_guests_paid < 20 * 3:
                accounts_for_free = 2
            if quantity_guests_paid >= 20 * 1 and quantity_guests_paid < 20 * 2:
                accounts_for_free = 1
            if quantity_guests_paid >= 0 and quantity_guests_paid < 20 * 1:
                accounts_for_free = 0
            all_accounts_to_buy = 4
            accounts_to_count_price = all_accounts_to_buy - accounts_for_free
            accounts_w_full_price = accounts_to_count_price - 1
 
            ost_discount = (quantity_guests_paid_last - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
            counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100    

            text = (
                f"{query.from_user.full_name},\n"
                f"<b>Баланс:</b> {balance_all} $\n"
                f"<b>Ваша скидка в текущем месяце составляет:</b>  {quantity_guests_paid_last * DISCOUNT_BASE_PROCENTS} %\n"
                f"<b>Цена продления услуги с учетом скидки:</b>  {counted_price_last} $\n"
                f"<b>Бесплатных аккаунтов доступно:</b>  {accounts_for_free} \n"
                f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
                "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

                f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
                f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
                f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
                f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
                f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
                
            )
        
        context.user_data['accounts_amount'] = all_accounts_to_buy
        context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
        context.user_data['counted_price_last'] = counted_price_last
        # await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        

    # await query.edit_message_text(text=f"Selected option: {query.data}")
async def my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    balance_all = user_db.user_balance

    subscript_stop_1 = user_db.subscription_stop_id_1
    subscript_stop_2 = user_db.subscription_stop_id_2
    subscript_stop_3 = user_db.subscription_stop_id_3
    subscript_stop_4 = user_db.subscription_stop_id_4
    subscript_stop_5 = user_db.subscription_stop_id_5

    subs_stop_list = []
    subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    for subs in subs_stop_list:
        if subs["subscript_time"] is not None:
            if subs["subscript_time"] >= datetime_now_int:
                acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
                delta_ostatok = acc_time - datetime_now
                subs["subscript_delta"] = delta_ostatok.days
            else:
                subs["subscript_delta"] = 0
        else:
                subs["subscript_delta"] = 0

    delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]
    text = (
            f"{update.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
        )
    keyboard = [
        [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - настройки", callback_data="subscript_1_get_info")],
        [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - настройки", callback_data="subscript_2_get_info")],
        [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - настройки", callback_data="subscript_3_get_info")],
        [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - настройки", callback_data="subscript_4_get_info")],
        [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - настройки", callback_data="subscript_5_get_info")],
        [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
        [InlineKeyboardButton("Назад", callback_data="start")],
        # [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
    ]
    
    # context.user_data['accounts_amount'] = all_accounts_to_buy
    # context.user_data['quantity_guests_paid_last'] = quantity_guests_paid_last
    # context.user_data['counted_price_last'] = counted_price_last
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}', reply_markup=reply_markup, parse_mode="html")
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def subscript_1_get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    subscript_stop_1 = user_db.subscription_stop_id_1

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    if subscript_stop_1 is not None:
        if datetime_now_int <= subscript_stop_1:
            text = (
                f"Настройки для аккаунта 1: {SERVER_COUNTRY_1}:\n"
            )
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, parse_mode="html")

            chosen_server = user_db.subscription_server_id_1

            # async_api = None
            
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            await async_api.login()
            inbounds: list[Inbound] = await async_api.inbound.get_list()

            user_id = user_db.user_id
            # user_email = user_db.user_name
            user_email = str(user_id)+'-1'

            print(user_email)
            # user_email = 'y6ng9kkw'
            # print(user_email)
            # user_email = '362141454-1'

            vpn_ip = servers_list_of_dicts[chosen_server]['ip']

            client_setttings_string, img_path = get_client_settings_string(inbounds, user_email, vpn_ip)
            cont_bot = context.bot
            new_tg_id = user_db.user_id
            
            await tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path)

            text = (
                f"Акк 1: {SERVER_COUNTRY_1}: инфо.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                f"Акк 1: {SERVER_COUNTRY_1}: не активен.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        text = (
            f"Акк 1: {SERVER_COUNTRY_1}: не активен.\n"
        )
        keyboard = [
            [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def subscript_2_get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    subscript_stop_2 = user_db.subscription_stop_id_2

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    if subscript_stop_2 is not None:
        if datetime_now_int <= subscript_stop_2:
            text = (
                f"Настройки для аккаунта 2: {SERVER_COUNTRY_2}:\n"
            )
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, parse_mode="html")

            chosen_server = user_db.subscription_server_id_2

            # async_api = None
            
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            await async_api.login()
            inbounds: list[Inbound] = await async_api.inbound.get_list()

            user_id = user_db.user_id
            # user_email = user_db.user_name
            user_email = str(user_id)+'-2'

            print(user_email)
            # user_email = 'y6ng9kkw'
            # print(user_email)
            # user_email = '362141454-1'

            vpn_ip = servers_list_of_dicts[chosen_server]['ip']
            client_setttings_string, img_path = get_client_settings_string(inbounds, user_email, vpn_ip)
            cont_bot = context.bot
            new_tg_id = user_db.user_id
            
            await tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path)

            text = (
                f"Акк 2: {SERVER_COUNTRY_2}: инфо.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                f"Акк 2: {SERVER_COUNTRY_2}: не активен.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        text = (
            f"Акк 2: {SERVER_COUNTRY_2}: не активен.\n"
        )
        keyboard = [
            [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def subscript_3_get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    subscript_stop_3 = user_db.subscription_stop_id_3

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    if subscript_stop_3 is not None:
        if datetime_now_int <= subscript_stop_3:
            text = (
                f"Настройки для аккаунта 3: {SERVER_COUNTRY_3}:\n"
            )
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, parse_mode="html")

            chosen_server = user_db.subscription_server_id_3

            # async_api = None
            
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            await async_api.login()
            inbounds: list[Inbound] = await async_api.inbound.get_list()

            user_id = user_db.user_id
            # user_email = user_db.user_name
            user_email = str(user_id)+'-3'

            print(user_email)
            # user_email = 'y6ng9kkw'
            # print(user_email)
            # user_email = '362141454-1'

            vpn_ip = servers_list_of_dicts[chosen_server]['ip']
            client_setttings_string, img_path = get_client_settings_string(inbounds, user_email, vpn_ip)
            cont_bot = context.bot
            new_tg_id = user_db.user_id
            
            await tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path)

            text = (
                f"Акк 3: {SERVER_COUNTRY_3}: инфо.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                f"Акк 3: {SERVER_COUNTRY_3}: не активен.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        text = (
            f"Акк 3: {SERVER_COUNTRY_3}: не активен.\n"
        )
        keyboard = [
            [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def subscript_4_get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    subscript_stop_4 = user_db.subscription_stop_id_4

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    if subscript_stop_4 is not None:
        if datetime_now_int <= subscript_stop_4:
            text = (
                f"Настройки для аккаунта 4: {SERVER_COUNTRY_4}:\n"
            )
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, parse_mode="html")

            chosen_server = user_db.subscription_server_id_4

            # async_api = None
            
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            await async_api.login()
            inbounds: list[Inbound] = await async_api.inbound.get_list()

            user_id = user_db.user_id
            # user_email = user_db.user_name
            user_email = str(user_id)+'-4'

            print(user_email)
            # user_email = 'y6ng9kkw'
            # print(user_email)
            # user_email = '362141454-1'

            vpn_ip = servers_list_of_dicts[chosen_server]['ip']
            client_setttings_string, img_path = get_client_settings_string(inbounds, user_email, vpn_ip)
            cont_bot = context.bot
            new_tg_id = user_db.user_id
            
            await tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path)

            text = (
                f"Акк 4: {SERVER_COUNTRY_4}: инфо.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                f"Акк 4: {SERVER_COUNTRY_4}: не активен.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        text = (
            f"Акк 4: {SERVER_COUNTRY_4}: не активен.\n"
        )
        keyboard = [
            [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def subscript_5_get_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    subscript_stop_5 = user_db.subscription_stop_id_5

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    if subscript_stop_5 is not None:
        if datetime_now_int <= subscript_stop_5:
            text = (
                f"Настройки для аккаунта 5: {SERVER_COUNTRY_5}:\n"
            )
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, parse_mode="html")

            chosen_server = user_db.subscription_server_id_5

            # async_api = None
            
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            await async_api.login()
            inbounds: list[Inbound] = await async_api.inbound.get_list()

            user_id = user_db.user_id
            # user_email = user_db.user_name
            user_email = str(user_id)+'-5'

            print(user_email)
            # user_email = 'y6ng9kkw'
            # print(user_email)
            # user_email = '362141454-1'

            vpn_ip = servers_list_of_dicts[chosen_server]['ip']
            client_setttings_string, img_path = get_client_settings_string(inbounds, user_email, vpn_ip)
            cont_bot = context.bot
            new_tg_id = user_db.user_id
            
            await tg_send_user_settings_string_and_qr_code_then_del_qr(cont_bot, new_tg_id, client_setttings_string, img_path)

            text = (
                f"Акк 5: {SERVER_COUNTRY_5}: инфо.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                f"Акк 5: {SERVER_COUNTRY_5}: не активен.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
            # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        text = (
            f"Акк 5: {SERVER_COUNTRY_5}: не активен.\n"
        )
        keyboard = [
            [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="html")
        # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def balance_top_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
    balance_all = user_db.user_balance

    text = (
            f"{update.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Минимальный платеж:</b> {UPDATED_MIN_PAY} $*\n"
            "*Если платеж меньше минимального, то счет выставится на сумму мин. платежа, остаток зачислится на ваш баланс.\n"

        )
    keyboard = [
        [InlineKeyboardButton("+ 10 $", callback_data="balance_top_up_1")],
        [InlineKeyboardButton("+ 15 $", callback_data="balance_top_up_2")],
        [InlineKeyboardButton("+ 20 $", callback_data="balance_top_up_3")],
        [InlineKeyboardButton("+ 25 $", callback_data="balance_top_up_4")],
        [InlineKeyboardButton("+ 30 $", callback_data="balance_top_up_5")],
        [InlineKeyboardButton("Пополнить", callback_data="confirm_top_up_balance")],
        [InlineKeyboardButton("Назад", callback_data="start")],

    ]
    context.user_data['accounts_autopay'] = 0
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}', reply_markup=reply_markup, parse_mode="html")
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def auto_pay_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_db = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()

    balance_all = user_db.user_balance

    subscript_stop_1 = user_db.subscription_stop_id_1
    subscript_stop_2 = user_db.subscription_stop_id_2
    subscript_stop_3 = user_db.subscription_stop_id_3
    subscript_stop_4 = user_db.subscription_stop_id_4
    subscript_stop_5 = user_db.subscription_stop_id_5

    subsc_auto_pay_1 = None
    subsc_auto_pay_2 = None
    subsc_auto_pay_3 = None
    subsc_auto_pay_4 = None
    subsc_auto_pay_5 = None
    if user_db.subscription_autopay_id_1 == 0:
        subsc_auto_pay_1 = 'Отключен'
    else:
        subsc_auto_pay_1 = 'Включен'
    if user_db.subscription_autopay_id_2 == 0:
        subsc_auto_pay_2 = 'Отключен'
    else:
        subsc_auto_pay_2 = 'Включен'
    if user_db.subscription_autopay_id_3 == 0:
        subsc_auto_pay_3 = 'Отключен'
    else:
        subsc_auto_pay_3 = 'Включен'
    if user_db.subscription_autopay_id_4 == 0:
        subsc_auto_pay_4 = 'Отключен'
    else:
        subsc_auto_pay_4 = 'Включен'
    if user_db.subscription_autopay_id_5 == 0:
        subsc_auto_pay_5 = 'Отключен'
    else:
        subsc_auto_pay_5 = 'Включен'

    subs_stop_list = []
    subs_stop_list.append({"subscript_time":subscript_stop_1,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_2,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_3,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_4,"subscript_delta":None})
    subs_stop_list.append({"subscript_time":subscript_stop_5,"subscript_delta":None})

    datetime_now = datetime.now(timezone.utc)
    datetime_now_int = int(str(datetime_now.timestamp()*1000)[:13])

    for subs in subs_stop_list:
        if subs["subscript_time"] is not None:
            if subs["subscript_time"] >= datetime_now_int:
                acc_time = datetime.fromtimestamp(int(str(subs["subscript_time"])[:10])).astimezone(tz=timezone.utc)
                delta_ostatok = acc_time - datetime_now
                subs["subscript_delta"] = delta_ostatok.days
            else:
                subs["subscript_delta"] = 0
        else:
                subs["subscript_delta"] = 0

    delta_ostatok_1 = subs_stop_list[0]["subscript_delta"]
    delta_ostatok_2 = subs_stop_list[1]["subscript_delta"]
    delta_ostatok_3 = subs_stop_list[2]["subscript_delta"]
    delta_ostatok_4 = subs_stop_list[3]["subscript_delta"]
    delta_ostatok_5 = subs_stop_list[4]["subscript_delta"]
    text = (
            f"{update.from_user.full_name},\n"
            f"<b>Баланс:</b> {balance_all} $\n"
            f"<b>Акк 1: {SERVER_COUNTRY_1}:</b> Осталось: {delta_ostatok_1} дней\n"
            f"Автоплатеж {subsc_auto_pay_1}\n\n"
            f"<b>Акк 2: {SERVER_COUNTRY_2}:</b> Осталось: {delta_ostatok_2} дней\n"
            f"Автоплатеж {subsc_auto_pay_2}\n\n"
            f"<b>Акк 3: {SERVER_COUNTRY_3}:</b> Осталось: {delta_ostatok_3} дней\n"
            f"Автоплатеж {subsc_auto_pay_3}\n\n"
            f"<b>Акк 4: {SERVER_COUNTRY_4}:</b> Осталось: {delta_ostatok_4} дней\n"
            f"Автоплатеж {subsc_auto_pay_4}\n\n"
            f"<b>Акк 5: {SERVER_COUNTRY_5}:</b> Осталось: {delta_ostatok_5} дней\n"
            f"Автоплатеж {subsc_auto_pay_5}\n\n"
        )
    keyboard = [
        [InlineKeyboardButton(f"Акк 1 - {SERVER_COUNTRY_1} - автоплатеж", callback_data="auto_pay_1")],
        [InlineKeyboardButton(f"Акк 2 - {SERVER_COUNTRY_2} - автоплатеж", callback_data="auto_pay_2")],
        [InlineKeyboardButton(f"Акк 3 - {SERVER_COUNTRY_3} - автоплатеж", callback_data="auto_pay_3")],
        [InlineKeyboardButton(f"Акк 4 - {SERVER_COUNTRY_4} - автоплатеж", callback_data="auto_pay_4")],
        [InlineKeyboardButton(f"Акк 5 - {SERVER_COUNTRY_5} - автоплатеж", callback_data="auto_pay_5")],
        [InlineKeyboardButton("Подтвердить изменения.", callback_data="confirm_auto_pay")],
        [InlineKeyboardButton("Назад", callback_data="start")],
        # [InlineKeyboardButton("Выставить счет \U0001F4B3", callback_data="create_invoice")],
    ]
    context.user_data['accounts_autopay'] = 0
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}', reply_markup=reply_markup, parse_mode="html")
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def usloviya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Условия использования:\n"
        f"Сервис {BOT_SHOP_NAME} создан исключительно в развлекательных целях.\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def pay_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Инструкция по оплате:\n"
        "Платите денюжкой.\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Как использовать сервис полностью Бесплатно:\n"
        "\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def call_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Если у вас возникли проблемы или вопроссы,\n"
        "Вы можете написать сообщение администратору.\n"
        "Для этого, нажмите: /send_mes_adm\n"
        "\n"
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    # await update.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="html")
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def send_mes_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        'Введите текст сообщения.\n'
        'Нажмите /cancel для отмены отправки\n'
    )
    await update.message.reply_text(text)
    # try:
    # await update.message.edit_text(text=text)
    return MESSTOADM

async def enter_mess_adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    text = (
        'Сообщение администратору:'
        f'from user: id: {update.message.from_user.id} \n'
        f'from user: name: {update.message.from_user.name} \n'
        f'from user: text: {update.message.text} \n'
    )
    await bot.send_message(chat_id=FIRST_USER_IN_DB, text=text)
    await bot.send_message(chat_id=update.message.from_user.id, text='Сообщение отправлено администратору.\nДождитесь ответа.\n')

    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    keyboard = [
        [InlineKeyboardButton("Главное меню", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # reply_markup=ReplyKeyboardRemove()
    # await update.message.reply_text(
    #     "Отмена отправки", reply_markup=ReplyKeyboardRemove()
    # )
    await update.message.reply_text(
        "Отмена отправки", reply_markup=reply_markup
    )

    # await update.message.edit_caption(caption="Отмена отправки", reply_markup=reply_markup, parse_mode="html")

    return ConversationHandler.END



async def admin_send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
    # if update.from_user.id == FIRST_USER_IN_DB:
        text = (
            "Отправить сообщение всем пользователям.\n"
            "Для этого, нажмите: /admin_send_all_mes\n"
            'Нажмите /cancel для отмены отправки\n'
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def admin_send_all_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.from_user.id)
    if update.message.from_user.id in admins_list:
        text = (
            "Введите текст сообщения пользователям.\n"
            'Нажмите /cancel для отмены отправки\n'
        )
        await update.message.reply_text(text)
        

        
        return TYPEMESSALL
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def admin_send_all_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        bot = context.bot
        all_users = session.query(AllUsers).all()

        text = (
                'Объявление от администратора:\n'
                f'{update.message.text} \n'
            )
        
        for user in all_users:
            await bot.send_message(chat_id=user.user_id, text=text)
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)



async def adm_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Получить инфу на юзера.\n"
            "Для этого, нажмите: /adm_user_info_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_user_info_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        
        return GETINFO
    else:
        text = (
            "У вас нет прав администратора."
        )
        await update.message.reply_text(text)

async def adm_user_info_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        get_id = int(update.message.text)
        all_users = session.query(AllUsers).all()
        info = None
        users_were_invited_by_him = []
        for user in all_users:
            if user.user_id_who_invited == get_id:
                users_were_invited_by_him.append(user.user_id)
            if user.user_id == get_id:
                sub_stop_1 = None
                sub_stop_2 = None
                sub_stop_3 = None
                sub_stop_4 = None
                sub_stop_5 = None
                if user.subscription_stop_id_1 is not None:
                    sub_stop_1 = datetime.fromtimestamp(int(str(user.subscription_stop_id_1)[:10])).astimezone(tz=timezone.utc)
                if user.subscription_stop_id_2 is not None:
                    sub_stop_2 = datetime.fromtimestamp(int(str(user.subscription_stop_id_2)[:10])).astimezone(tz=timezone.utc)
                if user.subscription_stop_id_3 is not None:
                    sub_stop_3 = datetime.fromtimestamp(int(str(user.subscription_stop_id_3)[:10])).astimezone(tz=timezone.utc)
                if user.subscription_stop_id_1 is not None:
                    sub_stop_4 = datetime.fromtimestamp(int(str(user.subscription_stop_id_4)[:10])).astimezone(tz=timezone.utc)
                if user.subscription_stop_id_1 is not None:
                    sub_stop_5 = datetime.fromtimestamp(int(str(user.subscription_stop_id_5)[:10])).astimezone(tz=timezone.utc)
                info = (
                    f'id = {user.user_id}\n'
                    f'name = {user.user_name}\n'
                    f'f_name = {user.user_full_name}\n'
                    f'who_invited = {user.user_id_who_invited}\n'

                    f'quant_guests_paid = {user.quantity_guests_paid}\n'
                    f'blocked = {user.user_blocked}\n'
                    f'user_time_rating = {user.user_time_rating}\n'
                    f'server_rating = {user.user_server_rating}\n'
                    f'balance = {user.user_balance}\n'
                    f'promo = {user.user_promo_new}\n'

                    f'is_partner = {user.is_partner}\n'
                    f'partner_procent = {user.partner_procent}\n'
                    f'partner_http = {user.partner_http}\n'
                    f'partner_wallet = {user.partner_wallet}\n'

                    f'total_earned = {user.total_earned}\n'
                    f'total_paid = {user.total_paid}\n'
                    f'last_pay = {user.last_pay}\n'

                    f'asked_redirect = {user.asked_redirect}\n'
                    f'asked_redirect_yes = {user.asked_redirect_yes}\n'
                    f'asked_time = {user.asked_time}\n'

                    f'server_id_1 = {user.subscription_server_id_1}\n'
                    f'autopay_id_1 = {user.subscription_autopay_id_1}\n'
                    f'stop_id_1 = {sub_stop_1}\n'

                    f'server_id_2 = {user.subscription_server_id_2}\n'
                    f'autopay_id_2 = {user.subscription_autopay_id_2}\n'
                    f'stop_id_2 = {sub_stop_2}\n'

                    f'server_id_3 = {user.subscription_server_id_3}\n'
                    f'autopay_id_3 = {user.subscription_autopay_id_3}\n'
                    f'stop_id_3 = {sub_stop_3}\n'

                    f'server_id_4 = {user.subscription_server_id_4}\n'
                    f'autopay_id_4 = {user.subscription_autopay_id_4}\n'
                    f'stop_id_4 = {sub_stop_4}\n'

                    f'server_id_5 = {user.subscription_server_id_5}\n'
                    f'autopay_id_5 = {user.subscription_autopay_id_5}\n'
                    f'stop_id_5 = {sub_stop_5}\n'
# 111
                )
        text = (
            f"Инфо на юзера {get_id}.\n"
            f"{info}\n"
            f"were invited by him:\n"
            f"{users_were_invited_by_him}\n"
        )
        await update.message.reply_text(text)
        
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, parse_mode="html")



async def adm_block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Заблокировать юзера.\n"
            "Для этого, нажмите: /adm_block_user_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_block_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        

        
        return BLOCKID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_block_user_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        us_id = int(update.message.text)
        user = session.query(AllUsers).filter_by(user_id=us_id).first()
        if user is not None:
            user.user_blocked = 1
            session.add(user)
            session.commit()
            text = (
                "Пользователь заблокирован."
            )
        else:
            text = (
                "Пользователь не найден."
            )
        await update.message.reply_text(text)
        return ConversationHandler.END
    
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)


# unblock user
async def adm_unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Разблокировать юзера.\n"
            "Для этого, нажмите: /adm_unblock_user_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_unblock_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        

        
        return UNBLOCKID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_unblock_user_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        us_id = int(update.message.text)
        user = session.query(AllUsers).filter_by(user_id=us_id).first()
        if user is not None:
            user.user_blocked = 0
            session.add(user)
            session.commit()
            text = (
                "Пользователь разблокирован."
            )
        else:
            text = (
                "Пользователь не найден."
            )
        await update.message.reply_text(text)
        return ConversationHandler.END
    
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)



async def adm_plus_usr_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Добавить дней к подписке.\n"
            "Для этого, нажмите: /adm_plus_usr_days_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_plus_usr_days_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            "Можно список через запятую,без пробелов.\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        
        return PLUSDAYSID #BLOCKID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_plus_usr_days_sub_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите номер подписки.(цифры) 1-5\n"
            "Можно список через запятую,без пробелов.\n"
            "Важно: если введен список id, то список подписок д-н соотв. каждому id!\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['id_of_user_to_days'] = update.message.text

        return PLUSDAYSSUB
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_plus_usr_days_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите сколько дней добавить.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['id_sub_days'] = update.message.text

        return PLUSDAYSDAYS
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_plus_usr_days_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        bot = context.bot
        user_to_days = context.user_data['id_of_user_to_days']
        user_to_days_splt = user_to_days.split(',')
        sub_id = context.user_data['id_sub_days']
        sub_id_splt = sub_id.split(',')
        for i in range(len(user_to_days_splt)):

            days_to_plus = int(update.message.text)
            new_tg_id= user_to_days_splt[i]
            subs_id = sub_id_splt[i]
            dayz = days_to_plus
            plus_some_days_to_sub(servers_list_of_dicts, new_tg_id, subs_id, dayz)

            text = (
                f'Вам добавлено {dayz} дней к подписке {subs_id}\n'
                f'Приятного использования. \n'
                'Нажмите /cancel для отмены\n'
            )
            await bot.send_message(chat_id=user_to_days, text=text)
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)



async def admin_mark_all_users_on_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Пометить всех юзеров на заблокированном сервере.\n"
            "Для этого, нажмите: /mark_users_on_server_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def mark_users_on_server_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID сервера, на котором отметить пользователей.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        
        # print(update.message.text)
        
        return CHOOSESERVER
    else:
        text = (
            "У вас нет прав администратора."
        )
        await update.message.reply_text(text)

async def mark_users_on_server_mark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        serv_id = int(update.message.text)
        all_users = session.query(AllUsers).all()
        for user in all_users:
            points_to_slizerin = 0
            if user.subscription_server_id_1 is not None:
                if user.subscription_server_id_1 == serv_id:
                    points_to_slizerin = 1
            if user.subscription_server_id_2 is not None:
                if user.subscription_server_id_2 == serv_id:
                    points_to_slizerin = 1
            if user.subscription_server_id_3 is not None:
                if user.subscription_server_id_3 == serv_id:
                    points_to_slizerin = 1
            if user.subscription_server_id_4 is not None:
                if user.subscription_server_id_4 == serv_id:
                    points_to_slizerin = 1
            if user.subscription_server_id_5 is not None:
                if user.subscription_server_id_5 == serv_id:
                    points_to_slizerin = 1
            if points_to_slizerin > 0:
                user.user_server_rating += 1
        session.add_all(all_users)
        session.commit()

        text = (
            "Пользователи отмечены.\n"
        )
        await update.message.reply_text(text)
        
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
        await update.message.reply_text(text)



async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Написать ответ пользователю от администратора."
            "Для этого, нажмите: /admin_reply_choose_user\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")


async def admin_reply_choose_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите телеграм ID пользователя, которому отправить ответ.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        # print('введеный текс:')
        # print(update.message.text)
        # context.user_data['id_of_user_to_reply'] = update.message.text
        return CHOOSEUSER
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def admin_reply_enter_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите текст сообщения.\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['id_of_user_to_reply'] = update.message.text

        return TYPEUSERID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def admin_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        bot = context.bot
        user_to_reply = context.user_data['id_of_user_to_reply']
        text = (
            'Ответ от администратора:\n'
            f'{update.message.text} \n'
        )
        await bot.send_message(chat_id=user_to_reply, text=text)
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)



# 111
async def adm_part_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:

        admin_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).first()
        admin_db.last_mnth_total_paid
        admin_db.total_paid
        admin_db.last_mnth_total_earned
        admin_db.total_earned
        admin_db.balance_earner
        admin_db.balance_earner_fact


        text = (
            "Статистика Админа:\n"
            f"Весь баланс: {admin_db.balance_earner}\n"
            f"Фактический баланс (уплаченный за подписки): {admin_db.balance_earner}\n"
            f"Всего получено на счет: {admin_db.total_earned}\n"
            f"Всего получено на счет за тек-й мес: {admin_db.last_mnth_total_earned}\n"
            f"Всего выплачено: {admin_db.total_paid}\n"
            f"Всего выплачено за тек-й мес: {admin_db.last_mnth_total_paid}\n"
        )
        # await update.message.reply_text(text)
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
    else:
        user = session.query(AllUsers).filter_by(user_id=update.from_user.id).first()
        # print(update.message.from_user.id)
        # print(update.from_user.id)
        # print(user)
        if user.is_partner is not None:
            if user.is_partner == 1:
                text = (
                    "Статистика Партнера:\n"
                    f"Весь баланс: {user.balance_earner}\n"
                    f"Фактический баланс (уплаченный за подписки): {user.balance_earner}\n"
                    f"Всего получено на счет: {user.total_earned}\n"
                    f"Всего получено на счет за тек-й мес: {user.last_mnth_total_earned}\n"
                    f"Всего выплачено: {user.total_paid}\n"
                    f"Всего выплачено за тек-й мес: {user.last_mnth_total_paid}\n"
                    "\n"
                    "* Выплаты за предыдущий месяц производятся в течении 5 рабочих дней в начале текущего."
                    "** Мин выплаты от 100 $"

                )
                keyboard = [
                    [InlineKeyboardButton("Главное меню", callback_data="start")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                # await update.message.reply_text(text)
                await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
            else:
                text = (
                    "У вас нет прав администратора.\n"
                )
                keyboard = [
                    [InlineKeyboardButton("Главное меню", callback_data="start")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                # await update.message.reply_text(text)
                await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
        else:
            text = (
                "У вас нет прав администратора.\n"
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # await update.message.reply_text(text)
            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def adm_add_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.from_user.id in admins_list:
        text = (
            "Добавить нового партнера.\n"
            "Для этого, нажмите: /adm_add_partner_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_add_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        
        return ADDPARTID #BLOCKID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_add_partner_prcnt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите процент выплат.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['part_user_id'] = update.message.text

        return ADDPARTPRC
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_add_partner_http(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите сайт, ютуб или тг канал.\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['part_percent'] = update.message.text

        return ADDPARTHTTP
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_add_partner_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите кошелек.\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['part_http'] = update.message.text

        return ADDPARTWLT
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_add_partner_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        bot = context.bot
        part_user_id = context.user_data['part_user_id']
        part_percent = context.user_data['part_percent']
        part_http = context.user_data['part_http']
        part_wallet = update.message.text

        user = session.query(AllUsers).filter_by(user_id=part_user_id).first()
        user.is_partner = 1
        user.partner_procent = part_percent
        user.partner_http = part_http
        user.partner_wallet = part_wallet

        new_tg_id= part_user_id
        if user.subscription_server_id_1:
            subs_id = 1
            dayz = 30
            await plus_some_days_to_sub(servers_list_of_dicts, new_tg_id, subs_id, dayz)
        else:
            # Тут должна выдаваться подписка, если сервер айди нет.
            subs_id = 1
            sub_days = 30
            new_client_email = new_tg_id
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])
            time_delta = timedelta(days=30)
            new_expiry_time = datetime_now + time_delta
            new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
            await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user, subs_id, sub_days)


        text = (
            'Вы внесены в список партнеров.\n'
            f'Процент с продаж: {part_percent}'
            f'Адрес: {part_http}'
            f'Кошелек для выплат: {part_wallet}'
            'Аккаунт бесплатно продлен на 30 дней'
            f'Приятного использования. \n'
        )
        await bot.send_message(chat_id=part_user_id, text=text)
        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
        await update.message.reply_text(text)



async def adm_show_partners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('show_p')
    print(update.from_user.id)
    if update.from_user.id in admins_list:
        all_users = session.query(AllUsers).all()
        partners_count = 0
        text = ''
        text_list = []
        for user in all_users:
            if user.is_partner is not None:
                if user.is_partner == 1:
                    part_id = user.user_id
                    part_name = user.user_name
                    part_proc = user.partner_procent
                    part_http = user.partner_http
                    part_wallet = user.partner_wallet
                    part_total_earn = user.total_earned
                    part_total_paid = user.total_paid
                    texts_found = str(
                        'Информация о партнерах: \n'
                        f'part_id: {part_id}\n'
                        f'part_name: {part_name}\n'
                        f'part_proc: {part_proc}\n'
                        f'part_http: {part_http}\n'
                        f'part_wallet: {part_wallet}\n'
                        f'part_total_earn: {part_total_earn}\n'
                        f'part_total_paid: {part_total_paid}\n'
                        '-----------------------\n'
                    )
                    text_list.append(texts_found)
                    # text = text+str(
                    #     'Информация о партнерах: \n'
                    #     f'part_id: {part_id}\n'
                    #     f'part_name: {part_name}\n'
                    #     f'part_proc: {part_proc}\n'
                    #     f'part_http: {part_http}\n'
                    #     f'part_wallet: {part_wallet}\n'
                    #     f'part_total_earn: {part_total_earn}\n'
                    #     f'part_total_paid: {part_total_paid}\n'
                    #     '-----------------------\n'
                    # )

                    partners_count += 1
        if partners_count > 0:
            # if partners_count % 10 == 0:
            for i in range(len(text_list)):
                text = text + text_list[i]
                if i == partners_count or i % 5 == 0:
                    await update.message.reply_text(text)
                    text = ''
        else:
            text = (
                "Партнеров не найдено."
            )
            keyboard = [
                [InlineKeyboardButton("Главное меню", callback_data="start")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
        await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def adm_pay_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message.from_user.id)
    if update.from_user.id in admins_list:
        text = (
            "Записать выплату партнеру.\n"
            "Для этого, нажмите: /adm_pay_partner_id\n"
            "\n"
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        text = (
            "У вас нет прав администратора."
        )
        keyboard = [
            [InlineKeyboardButton("Главное меню", callback_data="start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(text)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")

async def adm_pay_partner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите ID пользователя.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)
        
        return PAYPARTID #BLOCKID
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_pay_partner_sum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        text = (
            "Введите сумму выплаты в $.(цифры)\n"
            'Нажмите /cancel для отмены\n'
        )
        await update.message.reply_text(text)

        # print(update.message.text)
        context.user_data['part_pay_id'] = update.message.text

        return PAYPARTSUM
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)

async def adm_pay_partner_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in admins_list:
        bot = context.bot
        part_user_id = context.user_data['part_pay_id']
        part_pay_sum = update.message.text
        
        partner = session.query(AllUsers).filter_by(user_id=part_user_id).first()
        first_user_in_db_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).first()

        text = ''

        if part_pay_sum <= partner.balance_earner_fact and part_pay_sum <= first_user_in_db_db.balance_earner and part_pay_sum <= first_user_in_db_db.balance_earner_fact:

            part_wlt = partner.partner_wallet

            partner.total_paid += part_pay_sum
            partner.balance_earner_fact -= part_pay_sum
            session.add(partner)

            first_user_in_db_db.balance_earner -= part_pay_sum
            first_user_in_db_db.balance_earner_fact -= part_pay_sum
            session.add(first_user_in_db_db)

            # Записываем транзакцию партнерс!!!
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            transaction_prtnr_db = PartnerTransactions(
                user_id=part_user_id,
                trans_time=subscription_start_new,
                trans_ammount=part_pay_sum,
                trans_target='partner_spisanie',
                total_earned=partner.total_earned,
                total_paid=partner.total_paid,
                balance_earner=partner.balance_earner,
                balance_earner_fact=partner.balance_earner_fact,
                partner_wallet=part_wlt)
            
            session.add(transaction_prtnr_db)

            transaction_adm_db = PartnerTransactions(
                user_id=FIRST_USER_IN_DB,
                trans_time=subscription_start_new,
                trans_ammount=part_pay_sum,
                trans_target='adm_spisanie',
                total_earned=first_user_in_db_db.total_earned,
                total_paid=first_user_in_db_db.total_paid,
                balance_earner=first_user_in_db_db.balance_earner,
                balance_earner_fact=first_user_in_db_db.balance_earner_fact,
                partner_wallet=first_user_in_db_db.partner_wallet)
            
            session.add(transaction_adm_db)

            session.commit()

            text = (
                "Оплата проведена.\n"
            )
            await update.message.reply_text(text)

            text = (
                'Вам перечислена выплата за партнерство.\n'
                f'Сумма: {part_pay_sum} $ \n'
                f'Кошелек: {part_wlt} \n'
            )
            await bot.send_message(chat_id=part_user_id, text=text)
        else:
            text = (
                'Оплата не прошла.\n'
                'Не хватает средств\n'
                'Проверьте баланс партнера и админа\n'
                f'Партнер ID: {part_user_id} $ \n'
                f'Сумма: {part_pay_sum} $ \n'
                f'Кошелек: {part_wlt} \n'
                )
            await bot.send_message(chat_id=FIRST_USER_IN_DB, text=text)



        # print(update.message.text)
        # context.user_data['part_pay_sum'] = update.message.text

        return ConversationHandler.END
    else:
        text = (
            "У вас нет прав администратора."
        )
    await update.message.reply_text(text)
# help
# async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     help_text = (
#         "Доступные команды:\n"
#         "/start - Начать работу с ботом\n"
#         "/help - Показать это меню помощи\n"
#         "/count - Расчитать индивидуальную стоимость на 30 дней\n"
#         "/free - Использовать сервис полностью Бесплатно\n"
#         "/pluses - Преимущества сервиса\n"
#         "/settings - Настройка iphone, android, pc\n"
#         "/pay_help - Инструкция по оплате\n"
#         "/ref - Реферальная сылка\n"
#         "/usl - Условия использования\n"
#     )
#     # await query.edit_message_text(help_text)
#     await update.message.reply_text(help_text)



async def referal_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    # bot = Bot.initialize(TELEGRAM_TOKEN)
    # print(await bot)
    cont = str(update.from_user.id)
    url = helpers.create_deep_linked_url(bot.username, str(cont), group=False)
    # text = f"Бесплатный доступ в интернет без границ на 5 дней NoBordersShop:\n\n {url} \n"
    text = (
        f"\U0001F30E {BOT_SHOP_NAME} \U0001F525 \n"
        "Бесплатный доступ в интернет без границ:\n"
        "5 дней\n"
    )
    # keyboard = InlineKeyboardMarkup.from_button(
    #     InlineKeyboardButton(text="\U0001F381 Получить", url=url)
    # )
    keyboard = [
        [InlineKeyboardButton(text="\U0001F381 Получить", url=url)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}', reply_markup=keyboard)
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    text = "Установите приложения для своего устройства из списка на фото:\n"
    await update.message.reply_text(f'{text}')
    await bot.send_document(chat_id=update.message.chat_id, document=open('prilogeniya.jpg', 'rb'))
    text = ("Нажмите на плюс в правом верхнем углу приложения:\n"
            "Выберите пункт - Считать Qr код\n"
            "Наведите на полученный Qr код\n"
            "Разрешите изменение сетевых настроек\n\n"
            "Запускайте и Выключайте сервис через кнопку в приложении\n")
    keyboard = [
        [InlineKeyboardButton("Главное меню", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
            
    # await update.message.reply_text(f'{text}')
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")



async def pluses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = ("Наши плюсы:\n"
            "- Нет ограничения скорости\n"
            "- Нет ограничения трафика\n"
            "- Нет сбора и перепродажи личных данных\n"
            "- Нет рекламы (рекламу могут показывать приложения через которые вы подключаетесь к сервису)\n"
            "- Бесплатный промо период\n"
            "- Демократичные цены\n"
            "- Помесячная оплата\n"
            "- Есть возможность использования сервиса полностью бесплатно и без ограничений по скорости и трафику!\n"
            "- Автоматическое продление бесплатного использования при соблюдении всех условий\n"
            )
    
    keyboard = [
        [InlineKeyboardButton("Главное меню", callback_data="start")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # await update.message.reply_text(f'{text}')
    await update.message.edit_caption(caption=text, reply_markup=reply_markup, parse_mode="html")
# 123456


async def ask_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_in_db = session.query(AllUsers).filter_by(user_id=update.message.from_user.id).first()
    if user_in_db.user_blocked != 1:

        if user_in_db.asked_redirect == 1:
            user_in_db.asked_redirect_yes = 1
            session.add(user_in_db)
            # session.commit()

            ask = session.query(ReplaceAsks).filter_by(user_id=update.message.from_user.id).first()
            ask.asked_redirect_yes = 1
            session.add(ask)
            session.commit()


# -------------------------------------------------------TELEGRAM SHOP BOT END

    # await bot.send_document(chat_id=update.message.chat_id, document=open('test_qr.png', 'rb'))
# Chat invite link
# async def create_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     boto = Bot(TELEGRAM_TOKEN)
#     who_made_link = update.message.chat_id
#     # link = await boto.createChatInviteLink(chat_id=7721551877, expire_date=None, member_limit=None, name=who_made_link, creates_join_request=None, read_timeout=None, write_timeout=None, connect_timeout=None, pool_timeout=None, api_kwargs=None)
#     link = await boto.export_chat_invite_link(chat_id='@nobordersshopbot_bot')
#     await update.message.reply_text(f'ваша ссылка: {link}')

# show catalog
async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = session.query(Item).all()
    if items:
        message = "Каталог товаров:\n"
        for item in items:
            message += f"{item.name} - {item.price:.2f} RUB\n"
        message += "\nВведите название товара, чтобы добавить его в корзину."
    else:
        message = "Каталог пуст."
    await update.message.reply_text(message)

# tovar v korzinu
async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    item_name = update.message.text.strip()
    item = session.query(Item).filter_by(name=item_name).first()
    if item:
        cart_item = session.query(CartItem).filter_by(user_id=update.message.chat_id, item_id=item.id).first()
        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItem(user_id=update.message.chat_id, item_id=item.id, quantity=1)
            session.add(cart_item)
        session.commit()
        await update.message.reply_text(f"Товар '{item_name}' добавлен в корзину.")
    else:
        await update.message.reply_text("Товар не найден. Пожалуйста, введите корректное название товара.")

# pokaz korzini
async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart_items = session.query(CartItem).filter_by(user_id=update.message.chat_id).all()
    if cart_items:
        message = "Ваша корзина:\n"
        total = 0
        for cart_item in cart_items:
            item_total = cart_item.quantity * cart_item.item.price
            message += f"{cart_item.item.name} - {cart_item.quantity} шт. - {item_total:.2f} RUB\n"
            total += item_total
        message += f"\nИтого: {total:.2f} RUB"
        message += "\nВведите /checkout для оформления заказа."
        message += "\nВведите /clear_cart чтобы очистить корзину."
    else:
        message = "Ваша корзина пуста."
    await update.message.reply_text(message)

# oformlrnie zakaza
async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart_items = session.query(CartItem).filter_by(user_id=update.message.chat_id).all()
    if cart_items:
        title = "Оплата заказа"
        description = "Оплата товаров из вашей корзины"
        payload = "Custom-Payload"
        currency = "RUB"
        prices = [LabeledPrice(f"{item.item.name} ({item.quantity} шт.)", int(item.item.price * 100 * item.quantity)) for item in cart_items]
        await context.bot.send_invoice(
            chat_id=update.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency=currency,
            prices=prices,
            start_parameter="test-payment",
        )
    else:
        await update.message.reply_text("Ваша корзина пуста.")

# podtvergdenie oplati
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    if query.invoice_payload != "Custom-Payload":
        await query.answer(ok=False, error_message="Что-то пошло не так...")
    else:
        await query.answer(ok=True)

# Uspeshniy plateg
async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session.query(CartItem).filter_by(user_id=update.message.chat_id).delete()
    session.commit()
    await update.message.reply_text("Спасибо за покупку! Ваш заказ был успешно оформлен.")

# Ochistiit korzinu
async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cart_items = session.query(CartItem).filter_by(user_id=update.message.chat_id).all()
    # session.query(CartItem).filter_by(user_id=update.message.chat_id).delete()
    # print(cart_items)
    for item in cart_items:
        session.delete(item)
    session.commit()
    await update.message.reply_text("Ваша корзина пуста.")


# -------------------------------------------------------------------HELPFUL FUNCS FOR TELEGRAM SERVER

async def delete_invoices_from_db():
    del_days_year = 365
    del_days = 90 # через сколько дней удалять
    prolong_days = 5
    
    time_now = datetime.now(timezone.utc)

    invoices = session.query(AllInvoices).all()
    for invoice in invoices:
        invoice_created_time = datetime.fromisoformat(invoice.invoice_created_at).astimezone(tz=timezone.utc)
        invoice_created_time = format(invoice_created_time.strftime('%Y-%m-%d %H:%M:%S'))
        invoice_created_time = datetime.strptime(invoice_created_time, '%Y-%m-%d %H:%M:%S').astimezone(tz=timezone.utc)

        if (time_now - invoice_created_time).days >= del_days:
            session.delete(invoice)
    session.commit()

    transactions = session.query(AllTransactions).all()
    for transaction in transactions:
        transaction_created_time = datetime.fromtimestamp(int(str(transaction.trans_time)[:10])).astimezone(tz=timezone.utc)
        # transaction_created_time = datetime.fromisoformat(transaction.trans_time).astimezone()
        # transaction_created_time = format(transaction_created_time.strftime('%Y-%m-%d %H:%M:%S'))
        # transaction_created_time = datetime.strptime(transaction_created_time, '%Y-%m-%d %H:%M:%S')

        if (time_now - transaction_created_time).days >= del_days:
            session.delete(transaction)
    session.commit()

    partn_transactions = session.query(PartnerTransactions).all()
    for transaction in partn_transactions:
        transaction_created_time = datetime.fromtimestamp(int(str(transaction.trans_time)[:10])).astimezone(tz=timezone.utc)
        # transaction_created_time = datetime.fromisoformat(transaction.trans_time).astimezone()
        # transaction_created_time = format(transaction_created_time.strftime('%Y-%m-%d %H:%M:%S'))
        # transaction_created_time = datetime.strptime(transaction_created_time, '%Y-%m-%d %H:%M:%S')

        if (time_now - transaction_created_time).days >= del_days_year:
            session.delete(transaction)
    session.commit()

    users = session.query(AllUsers).all()
    for user in users:
        # if user.is_partner == 1:

        if user.user_promo_new == 0:
            if user.subscription_stop_id_1 is None and user.subscription_stop_id_2 is None and user.subscription_stop_id_3 is None and user.subscription_stop_id_4 is None and user.subscription_stop_id_5 is None:
                user_promo_created_time = datetime.fromtimestamp(int(str(user.user_promo_new_days)[:10])).astimezone(tz=timezone.utc)
                # user_promo_created_time = datetime.fromisoformat(user.user_promo_new_days).astimezone()
                # user_promo_created_time = format(user_promo_created_time.strftime('%Y-%m-%d %H:%M:%S'))
                # user_promo_created_time = datetime.strptime(user_promo_created_time, '%Y-%m-%d %H:%M:%S')
                if (time_now - user_promo_created_time).days >= del_days:

                    # datetime_now = datetime.now()
                    time_delta = timedelta(days=prolong_days)
                    new_expiry_time = time_now + time_delta
                    new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])

                    user.user_promo_new = 1
                    user.user_promo_new_days = new_expiry_time
                    session.add(user)
                    session.commit()

                    text = (
                        f'Активирована скидка 50% на {prolong_days} дней.\n'
                        'Приятного использования\n'
                    )
                    await send_message_to_user(user.user_id, text)

                    #  и тут сообщение отправляем, чтоб пользовался.



async def delete_depleted_users_with_db():

    del_days = 3 # через сколько дней удалять подписку неактивную.

    call_days = -5 # за сколько дней до окончания подписки слать уведомления (шлет каждый день пока не истечет)
    time_now = datetime.now(timezone.utc)

    servers = session.query(AllServers).all()

    all_users = session.query(AllUsers).all()
    for user in all_users:
        # напишем выдачу продление бесплатных подписок

        subs_id_not_prodlyaem = user.free_subs_given

        give_free_sub = 0
        if user.quantity_guests_paid >= 20 and user.quantity_guests_paid < 40:
            give_free_sub = 1
        if user.quantity_guests_paid >= 40 and user.quantity_guests_paid < 60:
            give_free_sub = 2
        if user.quantity_guests_paid >= 60 and user.quantity_guests_paid < 80:
            give_free_sub = 3
        if user.quantity_guests_paid >= 80 and user.quantity_guests_paid < 100:
            give_free_sub = 4
        if user.quantity_guests_paid >= 100:
            give_free_sub = 5
        if give_free_sub > 0:
            if give_free_sub == 1 and give_free_sub > subs_id_not_prodlyaem:
                subs_id = 1
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                user.free_subs_given = give_free_sub
                session.add(user)
                # session.commit()

                user_who_invited_id = user.user_id_who_invited
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                user_who_invited.quantity_guests_paid += 1
                session.add(user_who_invited)
                session.commit()

                # можно тут еще писать транзакцию за бесплатно

                subs_id_not_prodlyaem = give_free_sub
            
            if give_free_sub == 2 and give_free_sub > subs_id_not_prodlyaem:
                subs_id = 1
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 2
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                user.free_subs_given = give_free_sub
                session.add(user)
                # session.commit()
                
                user_who_invited_id = user.user_id_who_invited
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                user_who_invited.quantity_guests_paid += 2
                session.add(user_who_invited)
                session.commit()

                subs_id_not_prodlyaem = give_free_sub

            if give_free_sub == 3 and give_free_sub > subs_id_not_prodlyaem:
                subs_id = 1
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 2
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 3
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                user.free_subs_given = give_free_sub
                session.add(user)
                # session.commit()
                
                user_who_invited_id = user.user_id_who_invited
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                user_who_invited.quantity_guests_paid += 3
                session.add(user_who_invited)
                session.commit()

                subs_id_not_prodlyaem = give_free_sub

            if give_free_sub == 4 and give_free_sub > subs_id_not_prodlyaem:
                subs_id = 1
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 2
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 3
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 4
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                user.free_subs_given = give_free_sub
                session.add(user)
                # session.commit()
                
                user_who_invited_id = user.user_id_who_invited
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                user_who_invited.quantity_guests_paid += 4
                session.add(user_who_invited)
                session.commit()

                subs_id_not_prodlyaem = give_free_sub

            if give_free_sub == 5 and give_free_sub > subs_id_not_prodlyaem:
                subs_id = 1
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 2
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 3
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 4
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                subs_id = 5
                autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                user.free_subs_given = give_free_sub
                session.add(user)
                # session.commit()
                
                user_who_invited_id = user.user_id_who_invited
                user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                user_who_invited.quantity_guests_paid += 5
                session.add(user_who_invited)
                session.commit()

                subs_id_not_prodlyaem = give_free_sub


        
        # найдем самое ближайшее истечение подписки:
        sub_nearest_end = None
        if user.subscription_stop_id_1 is not None:
            sub_stop_delta_days = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_1)[:10])).astimezone(tz=timezone.utc)).days
            if sub_stop_delta_days <= 0:
                if sub_nearest_end is None or sub_nearest_end >= sub_stop_delta_days:
                    sub_nearest_end = sub_stop_delta_days
        if user.subscription_stop_id_2 is not None:
            sub_stop_delta_days = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_2)[:10])).astimezone(tz=timezone.utc)).days
            if sub_stop_delta_days <= 0:
                if sub_nearest_end is None or sub_nearest_end >= sub_stop_delta_days:
                    sub_nearest_end = sub_stop_delta_days
        if user.subscription_stop_id_3 is not None:
            sub_stop_delta_days = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_3)[:10])).astimezone(tz=timezone.utc)).days
            if sub_stop_delta_days <= 0:
                if sub_nearest_end is None or sub_nearest_end >= sub_stop_delta_days:
                    sub_nearest_end = sub_stop_delta_days
        if user.subscription_stop_id_4 is not None:
            sub_stop_delta_days = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_4)[:10])).astimezone(tz=timezone.utc)).days
            if sub_stop_delta_days <= 0:
                if sub_nearest_end is None or sub_nearest_end >= sub_stop_delta_days:
                    sub_nearest_end = sub_stop_delta_days
        if user.subscription_stop_id_5 is not None:
            sub_stop_delta_days = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_5)[:10])).astimezone(tz=timezone.utc)).days
            if sub_stop_delta_days <= 0:
                if sub_nearest_end is None or sub_nearest_end >= sub_stop_delta_days:
                    sub_nearest_end = sub_stop_delta_days

        if sub_nearest_end is not None:
            if sub_nearest_end >= call_days and sub_nearest_end <= 0:

                # автопродление платных подписок

                auto_accs = 0
                if user.subscription_autopay_id_1 == 1:
                    auto_accs = 1
                if user.subscription_autopay_id_2 == 1:
                    auto_accs = 2
                if user.subscription_autopay_id_3 == 1:
                    auto_accs = 3
                if user.subscription_autopay_id_4 == 1:
                    auto_accs = 4
                if user.subscription_autopay_id_5 == 1:
                    auto_accs = 5

                accounts_for_free = 0

                counted_price_last = None
                if user.user_promo_new == 1:
                    all_accounts_to_buy = auto_accs
                    counted_price_last = math.ceil((((UPDATED_PRICE * DISCOUNT_BASE_PROCENTS_PROMO) / 100) * all_accounts_to_buy)*100)/100 
 
                else:
                    
                    if user.quantity_guests_paid >= 20 * 5:
                        accounts_for_free = 5
                    if user.quantity_guests_paid >= 20 * 4 and user.quantity_guests_paid < 20 * 5:
                        accounts_for_free = 4
                    if user.quantity_guests_paid >= 20 * 3 and user.quantity_guests_paid < 20 * 4:
                        accounts_for_free = 3
                    if user.quantity_guests_paid >= 20 * 2 and user.quantity_guests_paid < 20 * 3:
                        accounts_for_free = 2
                    if user.quantity_guests_paid >= 20 * 1 and user.quantity_guests_paid < 20 * 2:
                        accounts_for_free = 1
                    if user.quantity_guests_paid >= 0 and user.quantity_guests_paid < 20 * 1:
                        accounts_for_free = 0

                    all_accounts_to_buy = auto_accs
                    accounts_to_count_price = all_accounts_to_buy - accounts_for_free
                    accounts_w_full_price = accounts_to_count_price - 1

                    ost_discount = (user.quantity_guests_paid - (20 * accounts_for_free)) * DISCOUNT_BASE_PROCENTS
                    counted_price_last = math.ceil(((UPDATED_PRICE * ((100 - ost_discount)/100)) + (accounts_w_full_price * UPDATED_PRICE))*100)/100  
 
                prodlenie_price_all = counted_price_last

                

                if user.user_balance >= prodlenie_price_all:
                    # то, продляем подписку, в другом случае шлем оповещение + пополнить баланс.
                    if auto_accs == 1:
                        subs_id = 1
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        user_who_invited_id = user.user_id_who_invited
                        user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                        user_who_invited.quantity_guests_paid += 1
                    
                    if auto_accs == 2:
                        subs_id = 1
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 2
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        user_who_invited_id = user.user_id_who_invited
                        user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                        user_who_invited.quantity_guests_paid += 2

                    if auto_accs == 3:
                        subs_id = 1
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 2
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 3
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        user_who_invited_id = user.user_id_who_invited
                        user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                        user_who_invited.quantity_guests_paid += 3

                    if auto_accs == 4:
                        subs_id = 1
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 2
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 3
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 4
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        user_who_invited_id = user.user_id_who_invited
                        user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                        user_who_invited.quantity_guests_paid += 4

                    if auto_accs == 5:
                        subs_id = 1
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 2
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 3
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 4
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        subs_id = 5
                        autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                        user_who_invited_id = user.user_id_who_invited
                        user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                        user_who_invited.quantity_guests_paid += 5

                    datetime_now = datetime.now(timezone.utc)
                    subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                    transaction_db = AllTransactions(user_id=user.user_id, trans_time=subscription_start_new, trans_ammount=prodlenie_price_all, trans_target='spisanie_autoprodlenie', accounts_ammount=auto_accs, quantity_guests_paid=user.quantity_guests_paid,promo=user.user_promo_new )
                    session.add(transaction_db)

                    # дальше начисляем партнеру в факт и админу в факт.

                    if user_who_invited.partner_procent:
                        procent_partnera = user_who_invited.partner_procent
                    else:
                        procent_partnera = STANDART_PARTNER_PROCENT
                    user_who_invited.total_earned += (prodlenie_price_all * procent_partnera)/100
                    user_who_invited.last_mnth_total_earned += (prodlenie_price_all * procent_partnera)/100
                    user_who_invited.balance_earner_fact += (prodlenie_price_all * procent_partnera)/100


                    user_who_invited.balance_earner += (prodlenie_price_all * procent_partnera)/100
                    
                
                    session.add(user_who_invited)

                    transaction_part_db = PartnerTransactions(
                    user_id=user_who_invited.user_id,
                    trans_time=subscription_start_new,
                    trans_ammount=(prodlenie_price_all * procent_partnera)/100,
                    trans_target='partner_popolnenie',
                    total_earned=user_who_invited.total_earned,
                    total_paid=user_who_invited.total_paid,
                    balance_earner=user_who_invited.balance_earner,
                    balance_earner_fact=user_who_invited.balance_earner_fact,
                    partner_wallet=user_who_invited.partner_wallet)
                
                    session.add(transaction_part_db)
                    # session.commit()

                    # Записываем админу поступление средств
                    first_user_in_db_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).first()

                    first_user_in_db_db.last_mnth_total_earned += prodlenie_price_all
                    first_user_in_db_db.total_earned += prodlenie_price_all
                    # first_user_in_db_db.balance_earner += prodlenie_price_all
                    first_user_in_db_db.balance_earner_fact += prodlenie_price_all

                    session.add(first_user_in_db_db)

                    transaction_adm_db = PartnerTransactions(
                        user_id=FIRST_USER_IN_DB,
                        trans_time=subscription_start_new,
                        trans_ammount=prodlenie_price_all,
                        trans_target='adm_popolnenie',
                        total_earned=first_user_in_db_db.total_earned,
                        total_paid=first_user_in_db_db.total_paid,
                        balance_earner=first_user_in_db_db.balance_earner,
                        balance_earner_fact=first_user_in_db_db.balance_earner_fact,
                        partner_wallet=first_user_in_db_db.partner_wallet)
                    
                    session.add(transaction_adm_db)

                    session.commit()



                    user.user_balance -= prodlenie_price_all
                    # user.quantity_guests_paid = 0
                    session.add(user)
                    session.commit()
                    auto_prod_text = (
                        'Подписка успешно продлена\n'
                        f'Списано: {prodlenie_price_all} $'
                        'Приятного использования\n'
                    )
                    await send_message_to_user(user.user_id, auto_prod_text)
                else:
                    if accounts_for_free > 0:
                        if accounts_for_free == 1:
                            subs_id = 1
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            user_who_invited_id = user.user_id_who_invited
                            user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                            user_who_invited.quantity_guests_paid += 1
                        
                        if accounts_for_free == 2:
                            subs_id = 1
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 2
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            user_who_invited_id = user.user_id_who_invited
                            user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                            user_who_invited.quantity_guests_paid += 2

                        if accounts_for_free == 3:
                            subs_id = 1
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 2
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 3
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            user_who_invited_id = user.user_id_who_invited
                            user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                            user_who_invited.quantity_guests_paid += 3

                        if accounts_for_free == 4:
                            subs_id = 1
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 2
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 3
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 4
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            user_who_invited_id = user.user_id_who_invited
                            user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                            user_who_invited.quantity_guests_paid += 4

                        if accounts_for_free == 5:
                            subs_id = 1
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 2
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 3
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 4
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            subs_id = 5
                            autoprodlenie_podpiski(user, subs_id, subs_id_not_prodlyaem)

                            user_who_invited_id = user.user_id_who_invited
                            user_who_invited = session.query(AllUsers).filter_by(user_id=user_who_invited_id).first()
                            user_who_invited.quantity_guests_paid += 5

                        datetime_now = datetime.now(timezone.utc)
                        subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                        transaction_db = AllTransactions(user_id=user.user_id, trans_time=subscription_start_new, trans_ammount=0.0, trans_target='spisanie_autoprodlenie', accounts_ammount=auto_accs, quantity_guests_paid=user.quantity_guests_paid,promo=user.user_promo_new )
                        session.add(transaction_db)
                        session.commit()



                        # user.user_balance -= prodlenie_price_all
                        user.quantity_guests_paid = 0
                        session.add(user)
                        session.commit()
                        auto_prod_text = (
                            'Бесплатные подписки успешно продлены\n'
                            
                            'Приятного использования\n'
                        )
                        await send_message_to_user(user.user_id, auto_prod_text)

                    prodlite_text = (
                        f'До окончания подписки осталось: {abs(sub_nearest_end)} дней.'
                        'Пожалуйста продлите подписку или пополните баланс.'
                    )
                    keyboard = [
                        [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await send_message_to_user(user.user_id, prodlite_text, reply_markup)

        if user.subscription_stop_id_1 is not None:
            sub_stop_delta_days_id_1 = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_1)[:10])).astimezone(tz=timezone.utc)).days

            # удаление деплитед подписок
            if sub_stop_delta_days_id_1 >= del_days:
                # user_email_1 = str(user.user_id) +'-1'
                chosen_server = user.subscription_server_id_1
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()
                await delete_client(async_api, user.user_id, 1)

                # Затем удаляем из бд параметры.
                user.subscription_server_id_1 = None
                user.subscription_stop_id_1 = None

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
            
            # оповещение о продлении
            if sub_stop_delta_days_id_1 >= call_days and sub_stop_delta_days_id_1 < 0:
                # chosen_server = user.subscription_server_id_1
                # async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                # await async_api.login()

                prodlite_text = (
                    f'До окончания подписки осталось: {abs(sub_stop_delta_days_id_1)} дней.'
                    'Пожалуйста продлите подписку или пополните баланс.'
                )
                keyboard = [
                    [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await send_message_to_user(user.user_id, prodlite_text, reply_markup)

            # # автопродление бесплатных подписок
            # if sub_stop_delta_days_id_1 >= call_days and sub_stop_delta_days_id_1 < 0 and user.quantity_guests_paid >= 20:
            #     chosen_server = user.subscription_server_id_1
            #     async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
            #     await async_api.login()

            #     subs_id = 1
            #     new_client_email = str(user.user_id)+'-1'
            #     client_setttings_string, img_path = await edit_user_at_server_and_return_settings(servers_list_of_dicts, new_client_email, user.user_id, user, subs_id)
            #     # await send_user_settings_string_and_qr_code_then_del_qr(user.user_id, client_setttings_string, img_path)
            #     # при автопродлении не обязательно сеттингс высылать и куар - можно просто сообщение, что подписка упешно продлена, приятного использования.
            #     # не забыть дописать +1 в quantity_guests_paid тому кто пригласил


        
        if user.subscription_stop_id_2 is not None:
            sub_stop_delta_days_id_2 = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_2)[:10])).astimezone(tz=timezone.utc)).days

            if sub_stop_delta_days_id_2 >= del_days:
                # user_email_1 = str(user.user_id) +'-1'
                chosen_server = user.subscription_server_id_2
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()
                await delete_client(async_api, user.user_id, 2)

                # Затем удаляем из бд параметры.
                user.subscription_server_id_2 = None
                user.subscription_stop_id_2 = None

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1

            # оповещение о продлении
            if sub_stop_delta_days_id_2 >= call_days and sub_stop_delta_days_id_2 < 0:
                chosen_server = user.subscription_server_id_2
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()

                prodlite_text = (
                    f'До окончания подписки осталось: {abs(sub_stop_delta_days_id_2)} дней.'
                    'Пожалуйста продлите подписку или пополните баланс.'
                )
                keyboard = [
                    [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await send_message_to_user(user.user_id, prodlite_text, reply_markup)

        if user.subscription_stop_id_3 is not None:
            sub_stop_delta_days_id_3 = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_3)[:10])).astimezone(tz=timezone.utc)).days

            if sub_stop_delta_days_id_3 >= del_days:
                # user_email_1 = str(user.user_id) +'-1'
                chosen_server = user.subscription_server_id_3
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()
                await delete_client(async_api, user.user_id, 3)

                # Затем удаляем из бд параметры.
                user.subscription_server_id_3 = None
                user.subscription_stop_id_3 = None

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
            
            # оповещение о продлении
            if sub_stop_delta_days_id_3 >= call_days and sub_stop_delta_days_id_3 < 0:
                chosen_server = user.subscription_server_id_3
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()

                prodlite_text = (
                    f'До окончания подписки осталось: {abs(sub_stop_delta_days_id_3)} дней.'
                    'Пожалуйста продлите подписку или пополните баланс.'
                )
                keyboard = [
                    [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await send_message_to_user(user.user_id, prodlite_text, reply_markup)

        if user.subscription_stop_id_4 is not None:
            sub_stop_delta_days_id_4 = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_4)[:10])).astimezone(tz=timezone.utc)).days

            if sub_stop_delta_days_id_4 >= del_days:
                # user_email_1 = str(user.user_id) +'-1'
                chosen_server = user.subscription_server_id_4
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()
                await delete_client(async_api, user.user_id, 4)

                # Затем удаляем из бд параметры.
                user.subscription_server_id_4 = None
                user.subscription_stop_id_4 = None

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1

            # оповещение о продлении
            if sub_stop_delta_days_id_4 >= call_days and sub_stop_delta_days_id_4 < 0:
                chosen_server = user.subscription_server_id_4
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()

                prodlite_text = (
                    f'До окончания подписки осталось: {abs(sub_stop_delta_days_id_4)} дней.'
                    'Пожалуйста продлите подписку или пополните баланс.'
                )
                keyboard = [
                    [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await send_message_to_user(user.user_id, prodlite_text, reply_markup)

        if user.subscription_stop_id_5 is not None:
            sub_stop_delta_days_id_5 = (time_now - datetime.fromtimestamp(int(str(user.subscription_stop_id_5)[:10])).astimezone(tz=timezone.utc)).days

            if sub_stop_delta_days_id_5 >= del_days:
                # user_email_1 = str(user.user_id) +'-1'
                chosen_server = user.subscription_server_id_5
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()
                await delete_client(async_api, user.user_id, 5)

                # Затем удаляем из бд параметры.
                user.subscription_server_id_5 = None
                user.subscription_stop_id_5 = None

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
            
            # оповещение о продлении
            if sub_stop_delta_days_id_5 >= call_days and sub_stop_delta_days_id_5 < 0:
                chosen_server = user.subscription_server_id_5
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
        
                await async_api.login()

                prodlite_text = (
                    f'До окончания подписки осталось: {abs(sub_stop_delta_days_id_5)} дней.'
                    'Пожалуйста продлите подписку или пополните баланс.'
                )
                keyboard = [
                    [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await send_message_to_user(user.user_id, prodlite_text, reply_markup)

    session.add_all(all_users)
    # session.commit()
    session.add_all(servers)
    session.commit()



async def database_clear_quantity_guests_paid():
    time_now = datetime.now(timezone.utc)

    func_res_time_db = session.query(FunctionsResultsTime).filter_by(function_name='db_clear_quant').first()

    # database_clear_quantity_guests_paid
    # if time_now.day == 1: # День месяца - после теста должен быть 1

    conv_date_str = datetime.fromisoformat(func_res_time_db.function_time)
    if (dt_month != conv_date_str.month) or (dt_month == conv_date_str.month and dt_year != conv_date_str.year):
  
        # тут открываем базу и для всех юзеров обнуляем quantity_guests_paid
        all_users = session.query(AllUsers).all()
        for user in all_users:
            if user.subscription_stop_id_1 is None and user.subscription_stop_id_2 is None and user.subscription_stop_id_3 is None and user.subscription_stop_id_4 is None and user.subscription_stop_id_5 is None:
                if user.quantity_guests_paid_potent >= 2:
                    text = (
                        'Информируем вас:\n'
                        f'по вашей ссылке используют сервис: {user.quantity_guests_paid_potent} человек\n'
                        f'при оплаченном аккаунте скидка составляла бы: {user.quantity_guests_paid_potent * DISCOUNT_BASE_PROCENTS} %\n'
                    )
                    keyboard = [
                        [InlineKeyboardButton("Использовать сервис полностью Бесплатно \U0001F525", callback_data="free")],
                        [InlineKeyboardButton("Расчитать стоимость \U0001F4B5", callback_data="count")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await send_message_to_user(user.user_id, text, reply_markup)
            user.quantity_guests_paid = 0
            user.quantity_guests_paid_potent = 0
            user.free_subs_given = 0

            if user.is_partner is not None:
                if user.is_partner == 1:
                    user.last_mnth_total_earned = 0
                    user.last_mnth_total_paid = 0
        session.add_all(all_users)

        func_res_time_db.function_time = str(time_now)
        session.commit()

async def make_subscriptions_from_queue():
    # 123
    sub_asks = session.query(AllSubscriptionsAwaited).all()
    if sub_asks:
        for ask in sub_asks:
            new_client_email = ask.user_id
            new_tg_id = ask.user_id
            subs_id = None
            sub_days = None
            if ask.subscr_id_1 != 0:
                subs_id = 1
                sub_days = ask.subscr_id_1
            if ask.subscr_id_2 != 0:
                subs_id = 2
                sub_days = ask.subscr_id_2
            if ask.subscr_id_3 != 0:
                subs_id = 3
                sub_days = ask.subscr_id_3
            if ask.subscr_id_4 != 0:
                subs_id = 4
                sub_days = ask.subscr_id_4
            if ask.subscr_id_5 != 0:
                subs_id = 5
                sub_days = ask.subscr_id_5

            user_paid = session.query(AllUsers).filter_by(user_id=new_tg_id).first()
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            time_delta = timedelta(days=sub_days)
            new_expiry_time = datetime_now + time_delta
            new_expiry_time = int(str(new_expiry_time.timestamp()*1000)[:13])
            await add_user_to_server_and_return_settings(servers_list_of_dicts, new_client_email, subscription_start_new, new_expiry_time,new_tg_id, user_paid, subs_id, sub_days)
            
            # session.delete(ask)
            session.commit()

            text_u = (
                f'Аккаунт номер {subs_id} - готов!/\n'
                'Перейдите во вкладку Аккаунты, и получите настройки.\n'
            )
            keyboard = [
                [InlineKeyboardButton("Мои Аккаунты", callback_data="my_accounts")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_message_to_user(new_tg_id, text_u, reply_markup)

            # А транзакции?

async def rplc_usrs_frm_blocked_srvr(blocked_server_id, new_server_id_1, new_server_id_2):
    # под это дело мы заранее долны создать сервера новые.
    # добавляем еще 1 сервак потом вместо заблокированного.

    # получаем из бд юзеров у которых 1-я, 2-я, 3, 4 ,5 подписка на заблоченном сервере
    users_on_srvr_sub_1 = session.query(AllUsers).filter_by(subscription_server_id_1=blocked_server_id).all()
    users_on_srvr_sub_2 = session.query(AllUsers).filter_by(subscription_server_id_2=blocked_server_id).all()
    users_on_srvr_sub_3 = session.query(AllUsers).filter_by(subscription_server_id_3=blocked_server_id).all()
    users_on_srvr_sub_4 = session.query(AllUsers).filter_by(subscription_server_id_4=blocked_server_id).all()
    users_on_srvr_sub_5 = session.query(AllUsers).filter_by(subscription_server_id_5=blocked_server_id).all()

    # получаем общее кол-во подписок на заблоч сервере
    subs_count = 0
    for subs in users_on_srvr_sub_1:
        subs_count += 1
    for subs in users_on_srvr_sub_2:
        subs_count += 1
    for subs in users_on_srvr_sub_3:
        subs_count += 1
    for subs in users_on_srvr_sub_4:
        subs_count += 1
    for subs in users_on_srvr_sub_5:
        subs_count += 1
    
    # получаем сколько подпис уйдет на 1-й сервак, а сколько на 2-й
    subs_to_serv_1 = subs_count // 2
    subs_to_serv_2 = subs_count - subs_to_serv_1

    # переносим подписки на новые сервера
    # думаю, нужна таблица - replaced_subs - где будут юзеры - sub_id1, 2,3,4,5 - new_sub_id1,2,3,4,5 - time
    servers = session.query(AllServers).all()

    subs_replaced = 0
    for subs in users_on_srvr_sub_1:
        if subs_replaced <= subs_to_serv_1:
            # перемещаем на 1-й сервак
            # сначала пишем в таблу перемещения
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_1
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
    
            await async_api.login()
            await delete_client(async_api, subs.user_id, 1)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_1 = None
            subs.subscription_stop_id_1 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 1
            chosen_server = new_server_id_1
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
            # пишем ее в бд
        else:
            # перемещаем на 2-й сервак
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_1
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)
    
            await async_api.login()
            await delete_client(async_api, subs.user_id, 1)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_1 = None
            subs.subscription_stop_id_1 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 1
            chosen_server = new_server_id_2
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
        subs_replaced += 1

    for subs in users_on_srvr_sub_2:
        if subs_replaced <= subs_to_serv_1:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_2
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 2)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_2 = None
            subs.subscription_stop_id_2 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 2
            chosen_server = new_server_id_1
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
        else:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_2
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 2)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_2 = None
            subs.subscription_stop_id_2 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 2
            chosen_server = new_server_id_2
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)

    for subs in users_on_srvr_sub_3:
        if subs_replaced <= subs_to_serv_1:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_3
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 3)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_3 = None
            subs.subscription_stop_id_3 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 3
            chosen_server = new_server_id_1
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
        else:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=None,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_3
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 3)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_3 = None
            subs.subscription_stop_id_3 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 3
            chosen_server = new_server_id_2
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)

    for subs in users_on_srvr_sub_4:
        if subs_replaced <= subs_to_serv_1:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_4
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 4)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_4 = None
            subs.subscription_stop_id_4 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 4
            chosen_server = new_server_id_1
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
        else:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=None)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_4
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 4)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_4 = None
            subs.subscription_stop_id_4 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 4
            chosen_server = new_server_id_2
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)

    for subs in users_on_srvr_sub_5:
        if subs_replaced <= subs_to_serv_1:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_5
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 5)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_5 = None
            subs.subscription_stop_id_5 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 5
            chosen_server = new_server_id_1
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
        else:
            datetime_now = datetime.now(timezone.utc)
            subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

            # time_delta = timedelta(days=sub_days)
            # new_expiry_time = datetime_now + time_delta
            # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

            subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5)
            # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
            session.add(subskr_replace)
            session.commit()

            # затем удаляем старую подписку

            chosen_server = subs.subscription_server_id_5
            async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

            await async_api.login()
            await delete_client(async_api, subs.user_id, 5)

            # Затем удаляем из бд параметры.
            subs.subscription_server_id_5 = None
            subs.subscription_stop_id_5 = None

            session.add(subs)
            session.commit()

            for server in servers:
                if server.id == chosen_server:
                    server.all_subscriptions -= 1
                    session.add(server)
                    session.commit()

            # затем создаем новую
            # new_client_email = subs.user_id
            new_tg_id = subs.user_id
            subs_id = 5
            chosen_server = new_server_id_2
            await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, subs, subs_id)
    


# функция определения рейтинга сервера
async def server_rating():
    all_users = session.query(AllUsers).all()

    servers = session.query(AllServers).all()

    for server in servers:
        server_id = server.id
        server_rating = 0
        unic_users = 0
        blocked_rating = 0
        for user in all_users:
            if user.subscription_server_id_1 == server_id or user.subscription_server_id_2 == server_id or user.subscription_server_id_3 == server_id or user.subscription_server_id_4 == server_id or user.subscription_server_id_5 == server_id:
                server_rating += user.user_time_rating
                unic_users += 1
                blocked_rating += user.user_server_rating

        rate = 0
        rate_b = 0
        if unic_users > 0:
            rate = server_rating / unic_users
            rate_b = blocked_rating / unic_users
        server.server_rating = rate
        server.blocked_rating = rate_b
    session.add_all(servers)
    session.commit()



async def replace_subs_from_queue():
    servers = session.query(AllServers).all()
    chosen_server = None
    max_subs = None
    total_subs = None
    for server in servers:
        if server.all_subscriptions < server.max_subscriptions and server.server_for_blocked == 1:
            chosen_server = int(server.id)
            max_subs = server.max_subscriptions
            total_subs = server.all_subscriptions
            break

    all_replaced_subs = session.query(ReplacedSubscriptions).all()
    for r_sub in all_replaced_subs:
        if total_subs < max_subs:
            if r_sub.replace_complited == 0:
                if r_sub.new_subscription_server_id_1:
                    new_tg_id = r_sub.user_id
                    subs_id = 1
                    # chosen_server = new_server_id_2
                    await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                    r_sub.replace_complited = 1
                    session.add(r_sub)
                    session.commit()


                if r_sub.new_subscription_server_id_2:
                    new_tg_id = r_sub.user_id
                    subs_id = 2
                    # chosen_server = new_server_id_2
                    await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                    r_sub.replace_complited = 1
                    session.add(r_sub)
                    session.commit()


                if r_sub.new_subscription_server_id_3:
                    new_tg_id = r_sub.user_id
                    subs_id = 3
                    # chosen_server = new_server_id_2
                    await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                    r_sub.replace_complited = 1
                    session.add(r_sub)
                    session.commit()


                if r_sub.new_subscription_server_id_4:
                    new_tg_id = r_sub.user_id
                    subs_id = 4
                    # chosen_server = new_server_id_2
                    await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                    r_sub.replace_complited = 1
                    session.add(r_sub)
                    session.commit()


                if r_sub.new_subscription_server_id_5:
                    new_tg_id = r_sub.user_id
                    subs_id = 5
                    # chosen_server = new_server_id_2
                    await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                    r_sub.replace_complited = 1
                    session.add(r_sub)
                    session.commit()

        else:
            
            text_u = (
                f'Кончилось место на сервере id:{chosen_server}\n'
            )
                # keyboard = [
                #     [InlineKeyboardButton("Мои Аккаунты", callback_data="my_accounts")],
                # ]
                # reply_markup = InlineKeyboardMarkup(keyboard)
            await send_message_to_user(FIRST_USER_IN_DB, text_u)


async def pack_users_by_rating():
    ask_period_days = 7
    users = session.query(AllUsers).order_by(desc(AllUsers.user_time_rating)).all()
    for user in users:
        if user.asked_redirect == 1 and user.asked_redirect_yes == 1:
            
            # тут запуск функции переноса подписки или добавление в очередь на перенос.
            await replace_subs_by_rating()

            user.asked_redirect = 0
            user.asked_redirect_yes = 0
            session.add(user)
            session.commit()

        

    servers = session.query(AllServers).order_by(desc(AllServers.server_rating)).all()
    for server in servers:
        if server.server_for_blocked != 1:
            for user in users:
                if user.asked_redirect == 0:
                    if user.user_blocked != 1 and user.user_time_rating > 0 and user.user_server_rating == 0:
                        datetime_now = datetime.now(timezone.utc)
                        last_ask_time = datetime.fromtimestamp(int(str(user.asked_time)[:10])).astimezone(tz=timezone.utc)

                        if (datetime_now - last_ask_time).days >= ask_period_days:
                            serv_id_1 = None
                            serv_id_2 = None
                            serv_id_3 = None
                            serv_id_4 = None
                            serv_id_5 = None

                            new_serv_id_1 = None
                            new_serv_id_2 = None
                            new_serv_id_3 = None
                            new_serv_id_4 = None
                            new_serv_id_5 = None

                            user_is_not_on_server = False

                            if server.country_id == 1:
                                serv_id_1 = user.subscription_server_id_1
                                new_serv_id_1 = server.id
                                if serv_id_1 != new_serv_id_1:
                                    user_is_not_on_server = True
                            if server.country_id == 2:
                                serv_id_2 = user.subscription_server_id_2
                                new_serv_id_2 = server.id
                                if serv_id_2 != new_serv_id_2:
                                    user_is_not_on_server = True
                            if server.country_id == 3:
                                serv_id_3 = user.subscription_server_id_3
                                new_serv_id_3 = server.id
                                if serv_id_3 != new_serv_id_3:
                                    user_is_not_on_server = True
                            if server.country_id == 4:
                                serv_id_4 = user.subscription_server_id_4
                                new_serv_id_4 = server.id
                                if serv_id_4 != new_serv_id_4:
                                    user_is_not_on_server = True
                            if server.country_id == 5:
                                serv_id_5 = user.subscription_server_id_5
                                new_serv_id_5 = server.id
                                if serv_id_5 != new_serv_id_5:
                                    user_is_not_on_server = True
                            
                            if user_is_not_on_server:
                                
                                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                                asks_replace = ReplaceAsks(user_id=user.user_id,replace_time=subscription_start_new,user_time_rating=user.user_time_rating,user_server_rating=user.user_server_rating, user_blocked=user.user_blocked, replace_complited=0,subscription_server_id_1=serv_id_1,subscription_server_id_2=serv_id_2,subscription_server_id_3=serv_id_3,subscription_server_id_4=serv_id_4,subscription_server_id_5=serv_id_5, new_subscription_server_id_1=new_serv_id_1,new_subscription_server_id_2=new_serv_id_2,new_subscription_server_id_3=new_serv_id_3,new_subscription_server_id_4=new_serv_id_4,new_subscription_server_id_5=new_serv_id_5)
                                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                                session.add(asks_replace)
                                # session.commit()

                                user.asked_time = subscription_start_new
                                user.asked_redirect = 1
                                session.add(user)
                                session.commit()

                                # то отправляем запрос на перенос
                                new_tg_id = user.user_id
                                text_u = (
                                    'В целях снижения риска блокировок сервера,\n'
                                    f'Предлагаем перенести подписку № {server.country_id}\n'
                                    'Перенос будет осуществлен в течении 48 часов\n'
                                    'Вам нужно будет сменить настройки устройства\n'
                                )
                                keyboard = [
                                    [InlineKeyboardButton("Согласен", callback_data=f"ask_confirm")],
                                ]
                                reply_markup = InlineKeyboardMarkup(keyboard)
                                await send_message_to_user(new_tg_id, text_u, reply_markup)


async def replace_subs_by_rating():
    # servers = session.query(AllServers).all()
    # chosen_server = None
    # max_subs = None
    # total_subs = None
    # for server in servers:
    #     if server.all_subscriptions < server.max_subscriptions and server.server_for_blocked == 1:
    #         chosen_server = int(server.id)
    #         max_subs = server.max_subscriptions
    #         total_subs = server.all_subscriptions
    #         break

    all_replaced_subs = session.query(ReplaceAsks).all()
    for r_sub in all_replaced_subs:
        # if total_subs < max_subs:
        if r_sub.replace_complited == 0 and r_sub.asked_redirect_yes == 1:
            if r_sub.new_subscription_server_id_1:
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                # time_delta = timedelta(days=sub_days)
                # new_expiry_time = datetime_now + time_delta
                # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

                subs = session.query(AllUsers).filter_by(user_id = r_sub.user_id).first()

                subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5,new_subscription_server_id_1=r_sub.new_subscription_server_id_1,new_subscription_server_id_2=r_sub.new_subscription_server_id_2,new_subscription_server_id_3=r_sub.new_subscription_server_id_3,new_subscription_server_id_4=r_sub.new_subscription_server_id_4,new_subscription_server_id_5=r_sub.new_subscription_server_id_5)
                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                session.add(subskr_replace)
                session.commit()

                # затем удаляем старую подписку

                chosen_server = subs.subscription_server_id_1
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

                await async_api.login()
                await delete_client(async_api, subs.user_id, 1)

                # Затем удаляем из бд параметры.
                subs.subscription_server_id_1 = None
                subs.subscription_stop_id_1 = None

                session.add(subs)
                session.commit()

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
                        session.add(server)
                        session.commit()
                        
                new_tg_id = r_sub.user_id
                subs_id = 1
                chosen_server = r_sub.new_subscription_server_id_1
                await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                subskr_replace.replace_complited = 1
                session.add(subskr_replace)
                session.commit()

                new_tg_id = subs.user_id
                text_u = (
                    # 'В целях снижения риска блокировок сервера,\n'
                    f'Подписка № {subs_id} успешно перенесена.\n'
                    'Измените настройки устройства\n'
                )
                keyboard = [
                    [InlineKeyboardButton("Получить настройки", callback_data=f"subscript_{subs_id}_get_info")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await send_message_to_user(new_tg_id, text_u, reply_markup)

            if r_sub.new_subscription_server_id_2:
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                # time_delta = timedelta(days=sub_days)
                # new_expiry_time = datetime_now + time_delta
                # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

                subs = session.query(AllUsers).filter_by(user_id = r_sub.user_id).first()

                subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5,new_subscription_server_id_1=r_sub.new_subscription_server_id_1,new_subscription_server_id_2=r_sub.new_subscription_server_id_2,new_subscription_server_id_3=r_sub.new_subscription_server_id_3,new_subscription_server_id_4=r_sub.new_subscription_server_id_4,new_subscription_server_id_5=r_sub.new_subscription_server_id_5)
                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                session.add(subskr_replace)
                session.commit()

                # затем удаляем старую подписку

                chosen_server = subs.subscription_server_id_2
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

                await async_api.login()
                await delete_client(async_api, subs.user_id, 2)

                # Затем удаляем из бд параметры.
                subs.subscription_server_id_2 = None
                subs.subscription_stop_id_2 = None

                session.add(subs)
                session.commit()

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
                        session.add(server)
                        session.commit()

                new_tg_id = r_sub.user_id
                subs_id = 2
                chosen_server = r_sub.new_subscription_server_id_2
                await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                subskr_replace.replace_complited = 1
                session.add(subskr_replace)
                session.commit()

                new_tg_id = subs.user_id
                text_u = (
                    # 'В целях снижения риска блокировок сервера,\n'
                    f'Подписка № {subs_id} успешно перенесена.\n'
                    'Измените настройки устройства\n'
                )
                keyboard = [
                    [InlineKeyboardButton("Получить настройки", callback_data=f"subscript_{subs_id}_get_info")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await send_message_to_user(new_tg_id, text_u, reply_markup)

            if r_sub.new_subscription_server_id_3:
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                # time_delta = timedelta(days=sub_days)
                # new_expiry_time = datetime_now + time_delta
                # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

                subs = session.query(AllUsers).filter_by(user_id = r_sub.user_id).first()

                subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5,new_subscription_server_id_1=r_sub.new_subscription_server_id_1,new_subscription_server_id_2=r_sub.new_subscription_server_id_2,new_subscription_server_id_3=r_sub.new_subscription_server_id_3,new_subscription_server_id_4=r_sub.new_subscription_server_id_4,new_subscription_server_id_5=r_sub.new_subscription_server_id_5)
                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                session.add(subskr_replace)
                session.commit()

                # затем удаляем старую подписку

                chosen_server = subs.subscription_server_id_3
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

                await async_api.login()
                await delete_client(async_api, subs.user_id, 3)

                # Затем удаляем из бд параметры.
                subs.subscription_server_id_3 = None
                subs.subscription_stop_id_3 = None

                session.add(subs)
                session.commit()

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
                        session.add(server)
                        session.commit()

                new_tg_id = r_sub.user_id
                subs_id = 3
                chosen_server = r_sub.new_subscription_server_id_3
                await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                subskr_replace.replace_complited = 1
                session.add(subskr_replace)
                session.commit()

                new_tg_id = subs.user_id
                text_u = (
                    # 'В целях снижения риска блокировок сервера,\n'
                    f'Подписка № {subs_id} успешно перенесена.\n'
                    'Измените настройки устройства\n'
                )
                keyboard = [
                    [InlineKeyboardButton("Получить настройки", callback_data=f"subscript_{subs_id}_get_info")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await send_message_to_user(new_tg_id, text_u, reply_markup)

            if r_sub.new_subscription_server_id_4:
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                # time_delta = timedelta(days=sub_days)
                # new_expiry_time = datetime_now + time_delta
                # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

                subs = session.query(AllUsers).filter_by(user_id = r_sub.user_id).first()

                subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5,new_subscription_server_id_1=r_sub.new_subscription_server_id_1,new_subscription_server_id_2=r_sub.new_subscription_server_id_2,new_subscription_server_id_3=r_sub.new_subscription_server_id_3,new_subscription_server_id_4=r_sub.new_subscription_server_id_4,new_subscription_server_id_5=r_sub.new_subscription_server_id_5)
                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                session.add(subskr_replace)
                session.commit()

                # затем удаляем старую подписку

                chosen_server = subs.subscription_server_id_4
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

                await async_api.login()
                await delete_client(async_api, subs.user_id, 4)

                # Затем удаляем из бд параметры.
                subs.subscription_server_id_4 = None
                subs.subscription_stop_id_4 = None

                session.add(subs)
                session.commit()

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
                        session.add(server)
                        session.commit()

                new_tg_id = r_sub.user_id
                subs_id = 4
                chosen_server = r_sub.new_subscription_server_id_4
                await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                subskr_replace.replace_complited = 1
                session.add(subskr_replace)
                session.commit()

                new_tg_id = subs.user_id
                text_u = (
                    # 'В целях снижения риска блокировок сервера,\n'
                    f'Подписка № {subs_id} успешно перенесена.\n'
                    'Измените настройки устройства\n'
                )
                keyboard = [
                    [InlineKeyboardButton("Получить настройки", callback_data=f"subscript_{subs_id}_get_info")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await send_message_to_user(new_tg_id, text_u, reply_markup)

            if r_sub.new_subscription_server_id_5:
                datetime_now = datetime.now(timezone.utc)
                subscription_start_new = int(str(datetime_now.timestamp()*1000)[:13])

                # time_delta = timedelta(days=sub_days)
                # new_expiry_time = datetime_now + time_delta
                # new_expiry_time = int(str(new_expiry_time.astimezone().timestamp()*1000)[:13])

                subs = session.query(AllUsers).filter_by(user_id = r_sub.user_id).first()

                subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=None,subscription_server_id_2=None,subscription_server_id_3=None,subscription_server_id_4=None,subscription_server_id_5=subs.subscription_server_id_5,new_subscription_server_id_1=r_sub.new_subscription_server_id_1,new_subscription_server_id_2=r_sub.new_subscription_server_id_2,new_subscription_server_id_3=r_sub.new_subscription_server_id_3,new_subscription_server_id_4=r_sub.new_subscription_server_id_4,new_subscription_server_id_5=r_sub.new_subscription_server_id_5)
                # subskr_replace = ReplacedSubscriptions(user_id=subs.user_id,replace_time=subscription_start_new,user_time_rating=subs.user_time_rating,user_server_rating=subs.user_server_rating, user_blocked=subs.user_blocked, replace_complited=0,subscription_server_id_1=subs.subscription_server_id_1,subscription_server_id_2=subs.subscription_server_id_2,subscription_server_id_3=subs.subscription_server_id_3,subscription_server_id_4=subs.subscription_server_id_4,subscription_server_id_5=subs.subscription_server_id_5)
                session.add(subskr_replace)
                session.commit()

                # затем удаляем старую подписку

                chosen_server = subs.subscription_server_id_5
                async_api = AsyncApi(host = servers_list_of_dicts[chosen_server]['http'], username = servers_list_of_dicts[chosen_server]['username'], password = servers_list_of_dicts[chosen_server]['pass'], token = servers_list_of_dicts[chosen_server]['token'], use_tls_verify =True, custom_certificate_path=servers_list_of_dicts[chosen_server]['sert'], logger=None)

                await async_api.login()
                await delete_client(async_api, subs.user_id, 5)

                # Затем удаляем из бд параметры.
                subs.subscription_server_id_5 = None
                subs.subscription_stop_id_5 = None

                session.add(subs)
                session.commit()

                for server in servers:
                    if server.id == chosen_server:
                        server.all_subscriptions -= 1
                        session.add(server)
                        session.commit()

                new_tg_id = r_sub.user_id
                subs_id = 5
                chosen_server = r_sub.new_subscription_server_id_5
                await add_user_to_spec_server(servers_list_of_dicts, chosen_server, new_tg_id, r_sub, subs_id)

                subskr_replace.replace_complited = 1
                session.add(subskr_replace)
                session.commit()

                new_tg_id = subs.user_id
                text_u = (
                    # 'В целях снижения риска блокировок сервера,\n'
                    f'Подписка № {subs_id} успешно перенесена.\n'
                    'Измените настройки устройства\n'
                )
                keyboard = [
                    [InlineKeyboardButton("Получить настройки", callback_data=f"subscript_{subs_id}_get_info")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await send_message_to_user(new_tg_id, text_u, reply_markup)
        # else:
            
        #     text_u = (
        #         f'Кончилось место на сервере id:{chosen_server}\n'
        #     )
        #     await send_message_to_user(FIRST_USER_IN_DB, text_u)

async def get_admin_stats():
    admin = session.query(AllUsers).filter_by(user_id = FIRST_USER_IN_DB).first()
    invoices = session.query(AllInvoices).all()

    this_mnth_paid = 0
    prev_mnth_paid = 0

    this_mnth_paid_fact = 0
    prev_mnth_paid_fact = 0

    datetime_now = datetime.now(timezone.utc)
    for invoice in invoices:
        if invoice.invoice_status == 'paid':
            inv_update_time = datetime.fromtimestamp(int(str(invoice.invoice_updated_at)[:10])).astimezone(tz=timezone.utc)
            if datetime_now.month == inv_update_time.month and datetime_now.year == inv_update_time.year:
                this_mnth_paid += invoice.invoice_ammount
                this_mnth_paid_fact += invoice.invoice_ammount_fact
            if datetime_now.month == 1:
                if 12 == inv_update_time.month and datetime_now.year == (inv_update_time.year - 1):
                    prev_mnth_paid += invoice.invoice_ammount
                    prev_mnth_paid_fact += invoice.invoice_ammount_fact
            else:
                if (datetime_now.month - 1) == inv_update_time.month and datetime_now.year == inv_update_time.year:
                    prev_mnth_paid += invoice.invoice_ammount
                    prev_mnth_paid_fact += invoice.invoice_ammount_fact
    
    # id = Column(Integer, primary_key=True)
    # month = Column(Integer, nullable=False)
    # year
    # prev_mnth_earned = Column(Float, unique=False, nullable=True)
    # mnth_earned = Column(Float, unique=False, nullable=True)
    # prev_total_earned = Column(Float, unique=False, nullable=True)
    # total_earned = Column(Float, unique=False, nullable=True)

    # prev_mnth_earned_fact = Column(Float, unique=False, nullable=True)
    # mnth_earned_fact = Column(Float, unique=False, nullable=True)
    # prev_total_earned_fact = Column(Float, unique=False, nullable=True)
    # total_earned_fact = Column(Float, unique=False, nullable=True)
    
    admin_stats = session.query(AdminStats).filter_by(month=datetime_now.month, year=datetime_now.year).first()
    if admin_stats:
        # if datetime_now.day == 1:
        admin_stats.mnth_earned = this_mnth_paid
        admin_stats.total_earned = admin_stats.prev_total_earned + this_mnth_paid
        admin_stats.mnth_earned_fact = this_mnth_paid_fact
        admin_stats.total_earned_fact = admin_stats.prev_total_earned_fact + this_mnth_paid_fact
        session.add(admin_stats)
        session.commit()
        # else:
        #     admin_stats.total_earned = admin_stats.prev_total_earned + this_mnth_paid
        #     session.add(admin_stats)
        #     session.commit()
    else:
        if datetime_now.day == 1:
            prev_admin_stats = None
            if datetime_now.month == 1:
                prev_admin_stats = session.query(AdminStats).filter_by(month=12,year=datetime_now.year - 1).first()
            else:
                prev_admin_stats = session.query(AdminStats).filter_by(month=datetime_now.month - 1, year=datetime_now.year).first()
            
            if prev_admin_stats:
                prev_total_earned_last = prev_admin_stats.prev_total_earned + prev_mnth_paid
                total_earned_last = prev_total_earned_last + this_mnth_paid

                prev_total_earned_fact_last = prev_admin_stats.prev_total_earned_fact + prev_mnth_paid_fact
                total_earned_fact_last = prev_total_earned_fact_last + this_mnth_paid_fact

                admin_stats = AdminStats(
                    month = datetime_now.month,
                    year = datetime_now.year,
                    prev_mnth_earned=prev_mnth_paid,
                    mnth_earned=this_mnth_paid,
                    prev_total_earned=prev_total_earned_last,
                    total_earned=total_earned_last,

                    prev_mnth_earned_fact=prev_mnth_paid_fact,
                    mnth_earned_fact=this_mnth_paid_fact,
                    prev_total_earned_fact=prev_total_earned_fact_last,
                    total_earned_fact=total_earned_fact_last
                    )
                session.add(admin_stats)
                session.commit()
        else:
            prev_admin_stats = None
            if datetime_now.month == 1:
                prev_admin_stats = session.query(AdminStats).filter_by(month=12,year=datetime_now.year - 1).first()
            else:
                prev_admin_stats = session.query(AdminStats).filter_by(month=datetime_now.month - 1, year=datetime_now.year).first()
            
            if prev_admin_stats:
                prev_total_earned_last = prev_admin_stats.prev_total_earned
                total_earned_last = prev_total_earned_last + this_mnth_paid

                prev_total_earned_fact_last = prev_admin_stats.prev_total_earned_fact
                total_earned_fact_last = prev_total_earned_fact_last + this_mnth_paid_fact

                admin_stats = AdminStats(
                    month = datetime_now.month,
                    year = datetime_now.year,
                    prev_mnth_earned=prev_mnth_paid,
                    mnth_earned=this_mnth_paid,
                    prev_total_earned=prev_total_earned_last,
                    total_earned=total_earned_last,

                    prev_mnth_earned_fact=prev_mnth_paid_fact,
                    mnth_earned_fact=this_mnth_paid_fact,
                    prev_total_earned_fact=prev_total_earned_fact_last,
                    total_earned_fact=total_earned_fact_last
                    )
                session.add(admin_stats)
                session.commit()

    # как считать выплаты за месяц?
    # надо записывать сколько всего выплачено за текущий месяц - и итого

    # откуда мы узнаем сколько выплачено: при выплате - мы делаем запись в транзакции 
    # Сколько всего к выплате за текущий месяц - и итого
    # 
            


# -------------------------------------------------------------------HELPFUL FUNCS FOR TELEGRAM SERVER END

# -------------------------------------------------------------ASYNC TO SYNC FUNCS

def run_continuously(interval=1):
    """Continuously run, while executing pending jobs at each
    elapsed time interval.
    @return cease_continuous_run: threading. Event which can
    be set to cease continuous run. Please note that it is
    *intended behavior that run_continuously() does not run
    missed jobs*. For example, if you've registered a job that
    should run every minute and you set a continuous run
    interval of one hour then your job won't be run 60 times
    at each interval but only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls):
            while not cease_continuous_run.is_set():
                schedule.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run



def async_to_sync(awaitable):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e:
        if str(e).startswith('There is no current event loop in thread'):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        else:
            raise
    return loop.run_until_complete(awaitable)



def shedule_do_async_functions():

    prodlite_text = (
        f'До окончания подписки осталось: {abs(-5)} дней.'
        'Пожалуйста продлите подписку или пополните баланс.'
    )
    keyboard = [
        [InlineKeyboardButton("Продлить подписку \U0001F4B5", callback_data="count")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    async_to_sync(send_message_to_user(362141454, prodlite_text, reply_markup))

def shed_do_async_db_clear_quant():
    async_to_sync(database_clear_quantity_guests_paid())

def shed_do_async_del_invoices_db():
    async_to_sync(delete_invoices_from_db())

def shed_do_async_export_db():
    async_to_sync(export_tg_vpn_shop_db_to_admin())

def shed_do_async_del_call_autorenew_sync():
    async_to_sync(delete_depleted_users_with_db())

def shed_do_async_make_sub_que():
    async_to_sync(make_subscriptions_from_queue())

def shed_do_async_server_rating():
    async_to_sync(server_rating())

def shed_do_async_repl_fr_que():
    async_to_sync(replace_subs_from_queue())

def shed_do_async_admin_stats():
    async_to_sync(get_admin_stats())

def shed_do_auto_price_with_course():
    async_to_sync(auto_price_with_course())
# -------------------------------------------------------------ASYNC TO SYNC FUNCS END
def print_updated_price():
    print(UPDATED_PRICE)

def main():
    appl = Application.builder().token(TELEGRAM_TOKEN).build()


    # Добавляем обработчики команд
    appl.add_handler(CommandHandler("start", start))
    # appl.add_handler(CommandHandler("help", help_command))
    # appl.add_handler(CommandHandler("catalog", catalog))
    # appl.add_handler(CommandHandler("cart", view_cart))
    # appl.add_handler(CommandHandler("clear_cart", clear_cart))
    # appl.add_handler(CommandHandler("checkout", checkout))
    # appl.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_to_cart))
    # appl.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    # appl.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    appl.add_handler(CallbackQueryHandler(button))
    appl.add_handler(CommandHandler("create_invoice", bitpappa_create_invoice))
    appl.add_handler(CommandHandler("ref", referal_link))
    appl.add_handler(CommandHandler("settings", settings))
    appl.add_handler(CommandHandler("pluses", pluses))

    # appl.add_handler(CallbackQueryHandler(send_mes_adm, pattern='send_mes_adm'))
    # appl.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_mes_adm))
    # appl.add_handler(MessageHandler(filters.TEXT, main_handler))

    # написать админу
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("send_mes_adm", send_mes_adm)], #CommandHandler
        states={
            MESSTOADM: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_mess_adm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler)

    # ответ от админа
    conv_handler2 = ConversationHandler(
        entry_points=[CommandHandler("admin_reply_choose_user", admin_reply_choose_user)], #CommandHandler
        states={
            CHOOSEUSER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_enter_text)],
            TYPEUSERID: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reply_send)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler2)

    # пометитть юзеров
    conv_handler3 = ConversationHandler(
        entry_points=[CommandHandler("mark_users_on_server_id", mark_users_on_server_id)], #CommandHandler
        states={
            CHOOSESERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, mark_users_on_server_mark)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler3)

    # написать всем админ
    conv_handler4 = ConversationHandler(
        entry_points=[CommandHandler("admin_send_all_mes", admin_send_all_mes)], #CommandHandler
        states={
            TYPEMESSALL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_all_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler4)

    # получить инфу на юзера
    conv_handler5 = ConversationHandler(
        entry_points=[CommandHandler("adm_user_info_id", adm_user_info_id)], #CommandHandler
        states={
            GETINFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_user_info_get)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler5)

    # Заблокировать юзера
    conv_handler6 = ConversationHandler(
        entry_points=[CommandHandler("adm_block_user_id", adm_block_user_id)], #CommandHandler
        states={
            BLOCKID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_block_user_do)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler6)

    # Добавить дней к подписке юзера
    conv_handler7 = ConversationHandler(
        entry_points=[CommandHandler("adm_plus_usr_days_id", adm_plus_usr_days_id)], #CommandHandler
        states={
            PLUSDAYSID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_plus_usr_days_sub_num)],
            PLUSDAYSSUB: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_plus_usr_days_days)],
            PLUSDAYSDAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_plus_usr_days_do)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler7)

    # Добавить нового партнера
    conv_handler8 = ConversationHandler(
        entry_points=[CommandHandler("adm_add_partner_id", adm_add_partner_id)], #CommandHandler
        states={
            ADDPARTID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_partner_prcnt)],
            ADDPARTPRC: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_partner_http)],
            ADDPARTHTTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_partner_wallet)],
            ADDPARTWLT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_add_partner_do)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler8)

    # Сделать выплату партнеру
    conv_handler9 = ConversationHandler(
        entry_points=[CommandHandler("adm_pay_partner_id", adm_pay_partner_id)], #CommandHandler
        states={
            PAYPARTID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_pay_partner_sum)],
            PAYPARTSUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_pay_partner_do)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler9)

    # Разблокировать юзера
    conv_handler10 = ConversationHandler(
        entry_points=[CommandHandler("adm_unblock_user_id", adm_unblock_user_id)], #CommandHandler
        states={
            UNBLOCKID: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_unblock_user_do)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    appl.add_handler(conv_handler10)

    # updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # dp = updater.dispatcher

    # # Set webhook
    # dp.bot.set_webhook("https://example.com/webhook")
    # updater.start_polling()
    # updater.idle()

    # async with appl:
    #     await  appl.start()
    #     await  app.run()
    # # when some shutdown mechanism is triggered:
    #     await  appl.stop()
    # Запуск бота
    appl.run_polling()

class FlaskThread(threading.Thread):
    def run(self) -> None:
        # app.run(ssl_context='adhoc', host="127.0.0.1")
        app.run( host="127.0.0.1")


class TelegramThread(threading.Thread):
    def run(self) -> None:
        main()

# class SheduleThread(threading.Thread):
#     def run(self) -> None:
#         schedule.every().day.at("08:24").do(database_clear_quantity_guests_paid) # Тут стоит 5 утра потому что по москве это 3 часа ночи - минимум вероятности, что кто-то залезет
#         schedule.run_pending()
#         time.sleep(1)

if __name__ == '__main__':
    # Создаем несколько товаров при первом запуске
    # if not session.query(Item).first():
    #     session.add_all([
    #         Item(name="30 дней подписки noborders", price=200.0),
    #         Item(name="90 дней подписки noborders", price=600.0),
    #         Item(name="180 дней подписки noborders", price=1200.0)
    #     ])
        # session.commit()
    user_in_db = session.query(AllUsers).filter_by(user_id=FIRST_USER_IN_DB).all()
    if not user_in_db:
        datetime_now = datetime.now(timezone.utc)
        datetime_now = int(str(datetime_now.timestamp()*1000)[:13])
        db_user = AllUsers(user_id=FIRST_USER_IN_DB, user_name="@K_Danilevsky", user_full_name="Kirill",user_id_who_invited=FIRST_USER_IN_DB,quantity_guests_paid=int(0),quantity_guests_paid_potent=int(0), free_subs_given=0,subscription_autopay_id_1=0,subscription_autopay_id_2=0,subscription_autopay_id_3=0,subscription_autopay_id_4=0,subscription_autopay_id_5=0,user_promo_new=int(0),user_promo_new_days=datetime_now, user_time_rating=0,user_server_rating=0,user_blocked=0,user_balance=0)
        session.add(db_user)
    session.commit()
    
    # добавляем сервера  при запуске
    servers = session.query(AllServers).all() # pod voprosom - prover zachem 
    for s in range(len(servers_list_of_dicts)):
        server = session.query(AllServers).filter_by(id=s).first()
        if not server:
            serv = AllServers(id=s,max_subscriptions=servers_list_of_dicts[s]['max_users'],country=servers_list_of_dicts[s]['country'],country_id=servers_list_of_dicts[s]['country_id'],all_subscriptions=0,active_subscriptions=0,server_rating=0,server_for_blocked=servers_list_of_dicts[s]['server_for_blocked'], blocked_rating=0)
            session.add(serv)
    session.commit()
    
    # FunctionsResultsTime
    # добавляем базовые значения выполнения тайм функций в бд
    funcs_names = []
    funcs_names.append('db_clear_quant')
    funcs_names.append('del_call_autorenew_sync')
    funcs_names.append('export_db')
    funcs_names.append('del_invoices_db')
    funcs_names.append('make_sub_que')
    funcs_names.append('server_rating')
    funcs_names.append('repl_fr_que')
    funcs_names.append('admin_stats')
    funcs_names.append('auto_price_with_course')
    funcs_names.append('print_updated_price')
    # funcs_names.append('repl_fr_que')
    for f in funcs_names:
        func_res_time_db = session.query(FunctionsResultsTime).filter_by(function_name=f).first()
        if not func_res_time_db:
            func_db = FunctionsResultsTime(function_name=f)
            session.add(func_db)
    session.commit()


    func_res_time_db = session.query(FunctionsResultsTime).all()
    
    datetime_now = datetime.now(timezone.utc)
    dt_year = datetime_now.year
    dt_month = datetime_now.month
    dt_day = datetime_now.day
    dt_hour = datetime_now.hour
    dt_minute = datetime_now.minute
    for func in func_res_time_db:
        # для ежемесячных функций
        conv_date_str = datetime.fromisoformat(func.function_time)
        if (dt_month != conv_date_str.month) or (dt_month == conv_date_str.month and dt_year != conv_date_str.year):
            if func.function_name == 'db_clear_quant':
                shed_do_async_db_clear_quant()
            if func.function_name == 'del_invoices_db':
                shed_do_async_del_invoices_db()
        # для ежедневных функций
        if (dt_day != conv_date_str.day) or (dt_day == conv_date_str.day and dt_month != conv_date_str.month):
            if func.function_name == 'export_db':
                shed_do_async_export_db()
            if func.function_name == 'del_call_autorenew_sync':
                shed_do_async_del_call_autorenew_sync()
        # для часовых
        if (dt_hour != conv_date_str.hour) or (dt_hour == conv_date_str.hour and dt_day != conv_date_str.day):
            if func.function_name == 'auto_price_with_course':
                shed_do_auto_price_with_course()
        # для минутных
        if (dt_minute != conv_date_str.minute) or (dt_minute == conv_date_str.minute and dt_hour != conv_date_str.hour):
            if func.function_name == 'print_updated_price':
                print_updated_price()



    shed_do_auto_price_with_course()


    schedule.every().day.at("05:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_db_clear_quant) # Тут стоит 5 утра потому что по москве это 3 часа ночи - минимум вероятности, что кто-то залезет
    schedule.every().day.at("05:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_del_call_autorenew_sync)
    schedule.every().day.at("01:30", timezone_pytz("Etc/Greenwich")).do(shed_do_async_export_db)
    schedule.every().day.at("02:15", timezone_pytz("Etc/Greenwich")).do(shed_do_async_del_invoices_db)

    schedule.every().day.at("00:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_make_sub_que)
    schedule.every().day.at("06:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_make_sub_que)
    schedule.every().day.at("12:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_make_sub_que)
    schedule.every().day.at("18:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_make_sub_que)

    schedule.every().day.at("01:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_server_rating)

    schedule.every().day.at("01:15", timezone_pytz("Etc/Greenwich")).do(shed_do_async_repl_fr_que)

    schedule.every().day.at("00:48", timezone_pytz("Etc/Greenwich")).do(shedule_do_async_functions) # ubrat potom!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    schedule.every().day.at("01:00", timezone_pytz("Etc/Greenwich")).do(shed_do_async_admin_stats) 

    schedule.every().hour.at(":03", timezone_pytz("Etc/Greenwich")).do(shed_do_auto_price_with_course)

    schedule.every().minute.at(":00", timezone_pytz("Etc/Greenwich")).do(print_updated_price)
    
    stop_run_continuously =  run_continuously()
    # main()
    # app.run()
    # Thread(target=app.run()).start()
    # Thread(target=main).start()
    # Thread(target=app.run()).start()
    # app.run()

    # async_to_sync(lol1())

    
    flask_thread = FlaskThread()
    flask_thread.daemon = True
    flask_thread.start()

    # shedule_thread = SheduleThread()
    # shedule_thread.daemon = True
    # shedule_thread.start()

    main()

    # stops sheduler
    stop_run_continuously.set()