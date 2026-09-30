# Upgrade your existing PipelineWatch repo to v0.3

This package is meant to be copied **into your existing `PipelineWatch` Git repository**. It does not contain a `.git` directory, so your existing Git history and remote stay intact.

## 1. Start from a clean repo

From your existing repo:

```bash
cd ~/build_profile/PipelineWatch
git status
```

Commit or stash any work before continuing.

## 2. Copy the v0.3 files over the existing repo

If the downloaded folder is in `~/Downloads/PipelineWatch-Phase3-Combined`:

```bash
rsync -av ~/Downloads/PipelineWatch-Phase3-Combined/ ~/build_profile/PipelineWatch/
```

This also copies hidden files such as `.github/workflows/ci.yml` and `.env.example`.

## 3. Refresh dependencies and test

```bash
cd ~/build_profile/PipelineWatch
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Expected result for this package:

```text
8 passed
```

## 4. Review the changes

```bash
git status
git diff --stat
git diff
```

Make sure `.venv`, `.env`, `pipelinewatch.db`, Terraform state, and the generated Lambda zip are not staged.

## 5. Commit and push

```bash
git add .
git status
git commit -m "Add serverless AWS architecture and observability"
git push origin main
```

## 6. GitHub About section

On the repository page, click the gear icon next to **About** and use:

**Description**

> Cloud-native pipeline observability and recovery service using Python, FastAPI, AWS SQS, Lambda, DynamoDB, CloudWatch, and Terraform.

**Topics**

`python` `aws` `fastapi` `sqs` `lambda` `dynamodb` `cloudwatch` `terraform` `distributed-systems` `observability`

## 7. AWS deployment is optional

The project works locally with SQLite without deploying anything. Deploy only when you want to demonstrate the real AWS path:

```bash
cd infra
terraform init
terraform plan
terraform apply
```

After demonstrating it, destroy the resources to avoid unnecessary charges:

```bash
terraform destroy
```
