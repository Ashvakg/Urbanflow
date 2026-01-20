
# Bronze Layer
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project_name}-bronze-${var.environment}"

  tags = {
    Layer       = "Bronze"
    Project     = var.project_name
    Environment = var.environment
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

    # REQUIRED in newer AWS provider versions
    filter {
      prefix = "" # apply to all objects
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Silver Layer - Cleaned and processed data
resource "aws_s3_bucket" "silver" {
  bucket = "${var.project_name}-silver-${var.environment}" 

  tags = {
    Layer       = "Silver"
    Project     = var.project_name
    Environment = var.environment
  }
}

# gold Layer - Aggregated and business-level data
resource "aws_s3_bucket" "gold" {
  bucket = "${var.project_name}-gold-${var.environment}" # Change YOUR_NAME 
  tags = {
    Layer       = "Gold"
    Project     = var.project_name
    Environment = var.environment
  }
}

# DLQ Layer - Dead Letter Queue for failed messages
resource "aws_s3_bucket" "dlq" {
  bucket = "${var.project_name}-dlq-${var.environment}"
  tags = {
    Layer       = "DLQ"
    Project     = var.project_name
    Environment = var.environment
  }
}

# enabling lifecycle policy to transition objects to Glacier after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "dlq_lifecycle" {
  bucket = aws_s3_bucket.dlq.id
  rule {
    id     = "transition_to_glacier"
    status = "Enabled"

    # REQUIRED in newer AWS provider versions
    filter {
      prefix = "" # apply to all objects
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }
  }
}