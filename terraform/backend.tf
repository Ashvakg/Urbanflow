# This bucket will STORE your terraform.tfstate file
resource "aws_s3_bucket" "terraform_state" {
  bucket = "urbanflow-tfstate-terraform"  # Change YOUR_NAME
  
  tags = {
    Name = "Terraform State"
    Project = "UrbanFlow"
  }
}

# Enable versioning (so you can recover from bad state)
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Prevent accidental deletion
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "urbanflow-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  
  attribute {
    name = "LockID"
    type = "S"
  }
  
  tags = {
    Name = "Terraform State Lock"
    Project = "UrbanFlow"
  }
}