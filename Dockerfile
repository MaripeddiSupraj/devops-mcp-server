FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g. for Terraform, though ideally Terraform is installed here too)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Terraform (useful for the terraform tools)
RUN curl -fsSL https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_$(dpkg --print-architecture).zip -o terraform.zip \
    && unzip terraform.zip -d /usr/local/bin \
    && rm terraform.zip

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose SSE port if running in Server-Sent Events mode
EXPOSE 8000

# We use python -m app.server to ensure module resolution works properly.
# Also set transport to SSE so that when it runs in a container, it creates an HTTP endpoint.
ENV MCP_TRANSPORT=sse

# Use uvicorn directly if running FastMCP via fastapi, or just run the script
CMD ["python", "app/server.py"]
