# DevOps MCP Server

AI-native DevOps MCP server exposing Kubernetes, Terraform, Cloud Cost, and CI/CD tools for LLM agents.

## Features
- **🚨 Kubernetes**: Query pods, check crash loops
- **🏗️ Terraform**: Run `terraform plan` and analyze infra changes
- **💰 AWS Cost**: Query AWS Cost Explorer for billing estimates
- **🚀 CI/CD**: Quickly fetch pipeline status (Planned)

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running
```bash
python app/server.py
```
