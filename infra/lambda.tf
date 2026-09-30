data "archive_file" "worker" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/pipelinewatch-lambda.zip"

  excludes = [
    ".git/**",
    ".github/**",
    ".venv/**",
    "architecture/**",
    "infra/**",
    "tests/**",
    "README.md",
    ".env",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "pipelinewatch.db",
    "__pycache__"
  ]
}

resource "aws_lambda_function" "worker" {
  function_name    = "${var.project_name}-worker"
  role             = aws_iam_role.worker.arn
  handler          = "app.lambda_handler.handler"
  runtime          = "python3.11"
  filename         = data.archive_file.worker.output_path
  source_code_hash = data.archive_file.worker.output_base64sha256
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb

  environment {
    variables = {
      JOB_STORE         = "dynamodb"
      DYNAMODB_TABLE    = aws_dynamodb_table.jobs.name
      METRIC_NAMESPACE  = var.metric_namespace
      MAX_RECEIVE_COUNT = tostring(var.max_receive_count)
      LOG_LEVEL         = "INFO"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.worker_basic_logs,
    aws_iam_role_policy.worker
  ]

  tags = local.tags
}

resource "aws_lambda_event_source_mapping" "jobs" {
  event_source_arn                   = aws_sqs_queue.pipeline_jobs.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 1
  function_response_types            = ["ReportBatchItemFailures"]
  enabled                            = true
}
