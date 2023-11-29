terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
  required_version = ">= 0.13"
}

// Configure the Yandex.Cloud provider
provider "yandex" {
  service_account_key_file = "key.json"
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  zone                     = var.zone_region
}

 
resource "yandex_iam_service_account_static_access_key" "sa-static-key" {
  service_account_id = var.admin_id
  description        = "static access key for object storage"
}

resource "yandex_iam_service_account_api_key" "sa-api-key" {
  service_account_id =  var.admin_id
  description        = "ключ для Vision"
}
 
resource "yandex_storage_bucket" "vvot47-photo" {
  access_key = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
  bucket     = "vvot47-photo"
}

resource "yandex_storage_bucket" "vvot47-faces" {
  access_key = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
  bucket     = "vvot47-faces"
}

resource "yandex_message_queue" "vvot47-task" {
  name                        = "vvot47-task"
  visibility_timeout_seconds  = 30
  receive_wait_time_seconds   = 20
  message_retention_seconds   = 345600
  access_key                  = yandex_iam_service_account_static_access_key.sa-static-key.access_key
  secret_key                  = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
}

resource "yandex_ydb_database_serverless" "vvot47-db-photo-face" {
  name                = "vvot47-db-photo-face"
  deletion_protection = false

  serverless_database {
    enable_throttling_rcu_limit = false
    storage_size_limit          = 5 
  }
}

 resource "yandex_ydb_table" "vvot47-db-photo-face" {
  path = "vvot47-db-photo-face"
  connection_string = yandex_ydb_database_serverless.vvot47-db-photo-face.ydb_full_endpoint 
  
column {
      name = "storage_id"
      type = "String"
      not_null = true
    }
    column {
      name = "chat_id"
      type = "String"
      not_null = false
    }
    column {
      name = "name"
      type = "String"
      not_null = false
    }

  primary_key = ["storage_id"]
  
}

resource "yandex_function" "vvot47-face-detection" {
  name               = "vvot47-face-detection"
  description        = "Обработчик лиц фото"
  user_hash          = "face_detect_user_hash"
  runtime            = "python311"
  entrypoint         = "vvot47-face-detection.handler"
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = var.admin_id
  tags               = ["my_tag"]
  content {
    zip_filename = "vvot47-face-detection.zip"
  }
  environment = {
    QUEUE_NAME = yandex_message_queue.vvot47-task.name
    AWS_ACCESS_KEY_ID = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
    AWS_DEFAULT_REGION = var.aws_region
    API_KEY = yandex_iam_service_account_api_key.sa-api-key.secret_key
  }

}

resource "archive_file" "zip" {
  output_path = "vvot47-face-detection.zip"
  type        = "zip"
  source_dir = "./face-detection"
}


resource "yandex_function_trigger" "vvot47-photo" {
  name        = "vvot47-photo"
  description = "Триггер, который срабатывает при сохранении объекта в бакет"
  object_storage {
     bucket_id = yandex_storage_bucket.vvot47-photo.id
     create    = true
     update    = false
     batch_cutoff = false
  }
  function {
    id                 = yandex_function.vvot47-face-detection.id
    service_account_id = var.admin_id
  }
}


resource "yandex_function" "vvot47-face-cut" {
  name               = "vvot47-face-cut"
  description        = "Яндекс функция, которая режет лица на фото и отправляет в MQ"
  user_hash          = "face_cut_user_hash"
  runtime            = "python311"
  entrypoint         = "vvot47-face-cut.handler"
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = var.admin_id
  tags               = ["my_tag"]
  content {
    zip_filename = "vvot47-face-cut.zip"
  }
  environment = {
    PHOTO_BUCKET_NAME = yandex_storage_bucket.vvot47-photo.bucket
    FACES_BUCKET_NAME = yandex_storage_bucket.vvot47-faces.bucket
    TABLE_NAME = yandex_ydb_database_serverless.vvot47-db-photo-face.name
    AWS_ACCESS_KEY_ID = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
    AWS_DEFAULT_REGION = var.aws_region
    YDB_ACCESS_TOKEN_CREDENTIALS = var.iam_token
    YDB_ENDPOINT = yandex_ydb_database_serverless.vvot47-db-photo-face.ydb_full_endpoint 
    YDB_DATABASE = yandex_ydb_database_serverless.vvot47-db-photo-face.database_path
  }

}

resource "archive_file" "zip2" {
  output_path = "vvot47-face-cut.zip"
  type        = "zip"
  source_dir = "./face-cut"
}

resource "yandex_function_trigger" "vvot47-task" {
  name        = "vvot47-task"
  description = "Триггер, который срабатывает при получнии сообщения из MQ"
  message_queue {
    queue_id           =  yandex_message_queue.vvot47-task.arn
    service_account_id = var.admin_id
    batch_size         = "1"
    batch_cutoff       = "10"
  }
  function {
    id                 = yandex_function.vvot47-face-cut.id
    service_account_id = var.admin_id
  }
}


resource "yandex_api_gateway" "api-gw" {
  name        = "api-gw"
  description = "api gateway tg"
  spec = <<-EOT
    openapi: "3.0.0"
    info:
      version: 1.0.0
      title: Test API
    servers:
      - url: https://{yandex_api_gateway.api-gw.id}.apigw.yandexcloud.net
    paths:
      /:
        get:
          summary: Serve static file from Yandex Cloud Object Storage
          parameters:
            - name: face
              in: query
              required: true
              schema:
                type: string
              style: simple
              explode: false
          x-yc-apigateway-integration:
            type: object_storage
            bucket: vvot47-faces
            object: '{face}.jpg'
            error_object: error.html
            service_account_id: ${var.admin_id}
  EOT
}

resource "archive_file" "zip3" {
  output_path = "vvot47-boot.zip"
  type        = "zip"
  source_dir = "./boot"
}

resource "yandex_function" "vvot47-boot" {
  name               = "vvot47-boot"
  description        = "Яндекс функциия для тг бота"
  user_hash          = "boot_user_hash"
  runtime            = "python311"
  entrypoint         = "vvot47-boot.handler"
  memory             = "128"
  execution_timeout  = "60"
  service_account_id = var.admin_id
  tags               = ["my_tag"]
  content {
    zip_filename = "vvot47-boot.zip"
  }
  environment = {
    API_GATEWAY_ID = yandex_api_gateway.api-gw.id 
    FACES_BUCKET_NAME = yandex_storage_bucket.vvot47-faces.bucket
    AWS_ACCESS_KEY_ID = yandex_iam_service_account_static_access_key.sa-static-key.access_key
    AWS_SECRET_ACCESS_KEY = yandex_iam_service_account_static_access_key.sa-static-key.secret_key
    AWS_DEFAULT_REGION = var.aws_region
    YDB_ACCESS_TOKEN_CREDENTIALS = var.iam_token
    YDB_ENDPOINT = yandex_ydb_database_serverless.vvot47-db-photo-face.ydb_full_endpoint 
    YDB_DATABASE = yandex_ydb_database_serverless.vvot47-db-photo-face.database_path
    TGKEY = var.tgkey
    TABLE_NAME = yandex_ydb_database_serverless.vvot47-db-photo-face.name
  }

}

resource "yandex_function_iam_binding" "function-boot" {
  function_id = yandex_function.vvot47-boot.id
  role        = "functions.functionInvoker"
  members = [
    "system:allUsers",
  ]
}

data "http" "webhook" {
  url = "https://api.telegram.org/bot${var.tgkey}/setWebhook?url=https://functions.yandexcloud.net/${yandex_function.vvot47-boot.id}"
}