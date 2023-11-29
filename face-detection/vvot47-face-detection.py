#!/usr/bin/env python
#-*- coding: utf-8 -*-
#!pip install boto3

import json
import requests
import base64
import boto3
import os

API_KEY = os.getenv("API_KEY")
QUEUE_NAME = os.getenv("QUEUE_NAME")

def handler(event, context):
    folder_id = event['messages'][0]['event_metadata']['folder_id']
    bucket_id = event['messages'][0]['details']['bucket_id']
    object_id = event['messages'][0]['details']['object_id']

    print(f"ObjectId: {object_id}")
    print(f"FolderId: {folder_id}")
    print(f"BucketId: {bucket_id}")

    session = boto3.session.Session()
    s3 = session.client(
        service_name='s3',
        endpoint_url='https://storage.yandexcloud.net'
    )


    get_object_response = s3.get_object(Bucket=bucket_id, Key=object_id)
    print("get bucket with id " + bucket_id)

    url_yv = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
    encoded_content = encode_file(get_object_response['Body'])
    
    payload = {
        "folderId": folder_id,
        "analyze_specs": [
            {
                "content": encoded_content,
                "features": [
                    {
                        "type": "FACE_DETECTION"
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {API_KEY}"
    }

    response = requests.post(url_yv, json=payload, headers=headers)

    print("Get response from AI VISION")

    client = boto3.client(
        service_name='sqs',
        endpoint_url='https://message-queue.api.cloud.yandex.net',
        region_name='ru-central1'
    )

    queue_response = client.get_queue_url(
        QueueName=QUEUE_NAME
    )          
    queue_url = queue_response["QueueUrl"]

    faces = response.json()['results'][0]['results'][0]['faceDetection']['faces']
    for face in faces:
        new_face = {'objectId': object_id, 'boundingBox': face['boundingBox']}
        client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(new_face))
        print("Succesfully sent message")

    return {
        'statusCode': response.status_code,
    }

def encode_file(file):
  file_content = file.read()
  return base64.b64encode(file_content).decode("utf-8")