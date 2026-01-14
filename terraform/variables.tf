############################
# AWS Variables
############################

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used for tagging resources"
  type        = string
  default     = "urbanflow"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

############################
# Snowflake Variables
############################

variable "snowflake_organization_name" {
  description = "Snowflake organization name (first part of the Snowflake URL)"
  type        = string
}

variable "snowflake_account_name" {
  description = "Snowflake account name (second part of the Snowflake URL)"
  type        = string
}

variable "snowflake_user" {
  description = "Snowflake username"
  type        = string
}

variable "snowflake_password" {
  description = "Snowflake password (do NOT commit this)"
  type        = string
  sensitive   = true
}

variable "snowflake_role" {
  description = "Snowflake role to use"
  type        = string
  default     = "ACCOUNTADMIN"
}

variable "snowflake_warehouse" {
  description = "Snowflake warehouse name"
  type        = string
  default     = "URBANFLOW_WH"
}

############################
# S3 Bucket Names
############################

variable "bronze_bucket_name" {
  description = "S3 bucket name for Bronze layer"
  type        = string
}

variable "silver_bucket_name" {
  description = "S3 bucket name for Silver layer"
  type        = string
}

variable "gold_bucket_name" {
  description = "S3 bucket name for Gold layer"
  type        = string
}
