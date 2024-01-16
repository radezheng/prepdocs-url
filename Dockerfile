# Use a base image that includes PowerShell
FROM mcr.microsoft.com/powershell:latest

#install python 3.10
RUN apt-get update && apt-get install -y python3.10  python3.10-venv
WORKDIR /app

# Copy scripts directory into the Docker image
COPY ./scripts ./scripts


# Set the environment variables
ENV AZURE_FORMRECOGNIZER_SERVICE="di4rade-jpe" \
    AZURE_FORMRECOGNIZER_SERVICE_KEY="xxx" \
    AZURE_LOCATION="japaneast" \
    AZURE_OPENAI_EMB_DEPLOYMENT="emb002" \
    AZURE_OPENAI_EMB_MODEL_NAME="text-embedding-ada-002" \
    AZURE_SEARCH_ANALYZER_NAME="zh-Hans.lucene" \
    AZURE_SEARCH_INDEX="gptkbindex" \
    AZURE_SEARCH_QUERY_LANGUAGE="zh-CN" \
    AZURE_SEARCH_QUERY_SPELLER="none" \
    AZURE_SEARCH_SERVICE_ADMIN_KEY="xxx" \
    AZURE_SEARCH_SERVICE="aisearch-base-jpe" \
    AZURE_STORAGE_ACCOUNT="sa4rade" \
    AZURE_STORAGE_CONTAINER="rag" \
    AZURE_STORAGE_ACCOUNT_KEY="xxxx" \
    AZURE_SUBSCRIPTION_ID="xxx" \
    AZURE_TENANT_ID="xxx" \
    AZURE_USE_AUTHENTICATION="false" \
    OPENAI_HOST="azure" \
    OPENAI_API_KEY="xxxx"

# cd to /app, then run scripts/prepdocs.ps1 
CMD [ "pwsh", "-c", "cd /app; ./scripts/prepdocs.ps1" ]