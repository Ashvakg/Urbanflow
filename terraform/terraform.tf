terraform {
  backend "s3" {
    bucket         = "urbanflow-tfstate-terraform"
    key            = "urbanflow/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "urbanflow-terraform-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 0.100"
    }
  }
}
