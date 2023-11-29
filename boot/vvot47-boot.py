#!/usr/bin/env python
#-*- coding: utf-8 -*-
#!pip install boto3
#!pip3 install ydb
import requests
import json
import os
import boto3
import ydb
import uuid
from boto3.dynamodb.conditions import Key

WELCOME_MESSAGE = """
    /getface - получить изображени, которое необходимо назвать

    /find {name}, где {name} это имя заданное getface.

"""

endpoint=os.getenv("YDB_ENDPOINT")
database=os.getenv("YDB_DATABASE")
creds=ydb.AccessTokenCredentials(os.getenv("YDB_ACCESS_TOKEN_CREDENTIALS"))
FACES_BUCKET_NAME=os.getenv("FACES_BUCKET_NAME")
API_GATEWAY_ID = os.getenv("API_GATEWAY_ID")
TABLE_NAME = "`" + os.getenv("TABLE_NAME") + "`"

def handler(event, context):
    update = json.loads(event["body"])
    message = update["message"]
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]
    if "text" not in message:
        send_message(chat_id, "Ошибка")
    else:
        text = message["text"]
        if text == "/start" or text == "/help":
            send_message(chat_id, WELCOME_MESSAGE)
        elif text == "/getface":
            if number_photo_proccessing(chat_id) == 0:
                result = get_empty_photo(chat_id)
                if result is None:
                    send_message(chat_id, "Сейчас нет доступных фотографий, попробуйте позже")
                else:
                    send_photo_content(chat_id, str(result))
            else:
                send_message(chat_id, "У вас уже есть фото, назовите имя!")
        elif text.startswith("/find"):
            if not text.startswith("/find "):
                send_message(chat_id, "Неизвестная команда. Читайте /help")
            if len(text) < 7:
                send_message(chat_id, "Тут нужен аргумент функции, написанный после пробела!")
            else:
                name = text[6:]
                result = get_photo_by_name(name)
                if result is None:
                    send_message(chat_id, f"Фотографии с именем {name} не найдены.")
                else:
                    for img in result:
                        send_photo_content(chat_id, str(img.storage_id.decode('utf-8')))
        else:
            if text.startswith("/"):
                send_message(chat_id, "Неизвестная команда!")
            elif number_photo_proccessing(chat_id) != 0:
                apply_name(chat_id, text)
                send_message(chat_id, "Хорошо!")
            else:
                send_message(chat_id, "Ошибка")
    return {
        'statusCode': 200
    }

def send_message(chat_id, text):
    tgkey = os.environ["TGKEY"]
    url = f"https://api.telegram.org/bot{tgkey}/sendMessage"
    params = { "chat_id": chat_id, "text": text}
    print(requests.get(url=url, params=params))

def number_photo_proccessing(chat_id):
  driver = ydb.Driver(endpoint=endpoint, database=database, credentials=creds)
  with driver:
    driver.wait(fail_fast=True, timeout=10)
    session = driver.table_client.session().create()
    return session.transaction().execute("select count(*) as cnt from "+TABLE_NAME+" where chat_id = '"+str(chat_id)+"';", commit_tx=True)[0].rows[0].cnt

def get_empty_photo(chat_id):
    driver = ydb.Driver(endpoint=endpoint, database=database, credentials=creds)
    with driver:
      driver.wait(fail_fast=True, timeout=10)
      session = driver.table_client.session().create()
      rs = session.transaction().execute("select storage_id from "+TABLE_NAME+" where chat_id is null and name is null;", commit_tx=True)[0].rows
      if len(rs) == 0:
        return None
      else:
        item = str(rs[0].storage_id.decode('utf-8'))
        session.transaction().execute("update "+TABLE_NAME+" set chat_id = '" + str(chat_id) + "' where storage_id = '" + item + "'", commit_tx=True)
        return item

def get_photo_by_name(name):
  driver = ydb.Driver(endpoint=endpoint, database=database, credentials=creds)
  with driver:
    driver.wait(fail_fast=True, timeout=5)
    session = driver.table_client.session().create()
    result = session.transaction().execute("select storage_id, chat_id, name from "+TABLE_NAME+" where name = '" + str(name) + "';", commit_tx=True)[0].rows
    if len(result) == 0:
        return None
    else:
        return result

def apply_name(chat_id, name):
  driver = ydb.Driver(endpoint=endpoint, database=database, credentials=creds)
  with driver:
    driver.wait(fail_fast=True, timeout=5)
    session = driver.table_client.session().create()
    session.transaction().execute("update "+TABLE_NAME+" set name = '" + str(name) + "', chat_id = NULL where chat_id = '" + str(chat_id) + "';", commit_tx=True)

def send_photo_content(chat_id, storage_id):
    tgkey = os.environ["TGKEY"]
    storage_id = str(storage_id) + ".jpg"
    session = boto3.session.Session()
    s3 = session.client(service_name='s3', endpoint_url='https://storage.yandexcloud.net')
    photo = s3.get_object(Bucket=FACES_BUCKET_NAME,Key=storage_id)['Body']
    files = {'photo': photo.read()}
    status = requests.post(f"https://api.telegram.org/bot{tgkey}/sendPhoto?chat_id={chat_id}", files=files)
    print(status)
