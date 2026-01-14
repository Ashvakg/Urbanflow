# Provider = Which cloud you're using (AWS)
provider "aws" {
  region = "eu-central-1"
}

# Bronze Layer - Raw ingestion
resource "aws_s3_bucket" "bronze" {
  bucket = "urbanflow-bronze-terraform"  # Change YOUR_NAME
  
  tags = {
    Layer       = "Bronze"
    Project     = "UrbanFlow"
    Environment = "dev"
  }
}

# Enabling versioning on bronze bucket
resource "aws_s3_bucket_versioning" "bronze_versioning" {
  bucket = aws_s3_bucket.bronze.id
  versioning_configuration {
    status = "Enabled"
  }
}

# enabling lifecycle policy to transition objects to Glacier after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "bronze_lifecycle" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Silver Layer - Cleaned and processed data
resource "aws_s3_bucket" "silver" {
  bucket = "urbanflow-silver-terraform"  # Change YOUR_NAME 

  tags = {
    Layer       = "Silver"
    Project     = "UrbanFlow"
    Environment = "dev"
  }
}

# gold Layer - Aggregated and business-level data
resource "aws_s3_bucket" "gold" {
  bucket = "urbanflow-gold-terraform"  # Change YOUR_NAME 
  tags = {
    Layer       = "Gold"
    Project     = "UrbanFlow"
    Environment = "dev"
  }
}
