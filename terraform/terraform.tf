terraform {
  backend "s3" {
    bucket         = "urbanflow-tfstate-terraform"  # Must match your state bucket name
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
  }
}