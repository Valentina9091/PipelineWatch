terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_sqs_queue" "pipeline_dlq" {
  name                      = "${var.project_name}-dlq"
  message_retention_seconds = 1209600

  tags = local.tags
}

resource "aws_sqs_queue" "pipeline_jobs" {
  name                       = "${var.project_name}-jobs"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  receive_wait_time_seconds  = 20
  message_retention_seconds  = 345600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.pipeline_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = local.tags
}

locals {
  tags = {
    Project   = "PipelineWatch"
    ManagedBy = "Terraform"
  }
}
