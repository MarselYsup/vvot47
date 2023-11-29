variable "aws_region" {
  type        = string
  description = "AWS region"
  default = "ru-central1"
}

variable "tgkey" {
  type        = string
  description = "Telegram key"
}


variable "admin_id" {
  type        = string
  description = "Service account id with admin role"
}

variable "cloud_id" {
  type        = string
  description = "Cloud id"
}

variable "folder_id" {
  type        = string
  description = "Folder id"
}

variable "zone_region" {
  type        = string
  description = "Zone region"
  default = "ru-central1-a"
}

variable "iam_token" {
  type        = string
  description = "iam token"
}