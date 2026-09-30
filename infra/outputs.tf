output "pipeline_queue_url" {
  value = aws_sqs_queue.pipeline_jobs.url
}

output "pipeline_queue_arn" {
  value = aws_sqs_queue.pipeline_jobs.arn
}

output "pipeline_dlq_url" {
  value = aws_sqs_queue.pipeline_dlq.url
}

output "pipeline_dlq_arn" {
  value = aws_sqs_queue.pipeline_dlq.arn
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.jobs.name
}

output "lambda_function_name" {
  value = aws_lambda_function.worker.function_name
}

output "cloudwatch_dashboard" {
  value = aws_cloudwatch_dashboard.pipelinewatch.dashboard_name
}

output "alarm_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
