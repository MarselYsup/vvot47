#!/usr/bin/env python
#-*- coding: utf-8 -*-
#!pip install boto3
#!pip3 install Pillow

import json
import boto3
import io
import uuid
import PIL
from PIL import Image
from io import BytesIO
import ydb
import os

PHOTO_BUCKET_NAME = os.getenv("PHOTO_BUCKET_NAME")
FACES_BUCKET_NAME = os.getenv("FACES_BUCKET_NAME")
TABLE_NAME = os.getenv("TABLE_NAME")
DB_ENDPOINT = os.getenv("YDB_ENDPOINT")
DB_DATABASE = os.getenv("YDB_DATABASE")
DB_CREDENTIALS = ydb.AccessTokenCredentials(os.getenv("YDB_ACCESS_TOKEN_CREDENTIALS"))

def handler(event, context):
    data = event['messages'][0]['details']['message']['body']
    json_data = json.loads(data)
    vertices = json_data['boundingBox']['vertices']
    object_id = json_data['objectId']
    folder_id = event['messages'][0]['event_metadata']['folder_id']

    print(f"Vertices: {vertices}")
    print(f"ObjectId: {object_id}")
    print(f"FolderId: {folder_id}")

    x_coordinates = [int(vertex['x']) for vertex in vertices]
    y_coordinates = [int(vertex['y']) for vertex in vertices]
    x1, y1 = min(x_coordinates), min(y_coordinates)
    x2, y2 = max(x_coordinates), max(y_coordinates)

    session = boto3.session.Session()
    s3 = session.client(service_name='s3', endpoint_url='https://storage.yandexcloud.net')
    photo = s3.get_object(Bucket=PHOTO_BUCKET_NAME, Key=object_id)['Body']
    print("get photo from storage...")
    im = Image.open(BytesIO(photo.read())) 
    im_crop = im.crop((x1, y1, x2, y2))
    img_byte_arr = io.BytesIO()
    im_crop.save(img_byte_arr, format='JPEG')
    print("photo was cut")
    random_uuid = str(uuid.uuid4())
    uuid_with_suffix = random_uuid + '.jpg'
    s3.put_object(Bucket=FACES_BUCKET_NAME, Key=uuid_with_suffix, Body=img_byte_arr.getvalue(), StorageClass='STANDARD')
    print(uuid_with_suffix + " was added in bucket")

    driver = ydb.Driver(endpoint=DB_ENDPOINT, database=DB_DATABASE, credentials=DB_CREDENTIALS)
    with driver:
        driver.wait(fail_fast=True, timeout=5)
        session = driver.table_client.session().create()
        session.transaction().execute(f"INSERT INTO `{TABLE_NAME}` (storage_id, chat_id, name) VALUES ('{random_uuid}', null, null);", commit_tx=True)
        return {
            'statusCode': 200,
        }