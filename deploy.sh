
# load .env file
set -o allexport    
source .env
set +o allexport
echo $AZURE_FORMRECOGNIZER_SERVICE

# 打开系统分配的身份标识
az cognitiveservices account identity assign --name $AZURE_FORMRECOGNIZER_SERVICE --resource-group $DOCUMENT_INTELLIGENCE_RG    

#获取form recognizer的身份标识
AZURE_FORMRECOGNIZER_SERVICE_ID=$(az cognitiveservices account show --name $AZURE_FORMRECOGNIZER_SERVICE --resource-group $DOCUMENT_INTELLIGENCE_RG --query "identity.principalId" --output tsv)

#将form recognizer的身份标识赋予存储的访问权限
az role assignment create --role "Storage Blob Data Reader" --assignee $AZURE_FORMRECOGNIZER_SERVICE_ID --scope "/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/$STORAGE_RG/providers/Microsoft.Storage/storageAccounts/$AZURE_STORAGE_ACCOUNT"


docker build . -t radezheng/predoc_url 

#debug shell
docker run -it --env-file .env --rm radezheng/predoc_url pwsh


#run with env setting in .env file, delete the instance after running
docker run --env-file .env --rm radezheng/predoc_url

docker push radezheng/predoc_url

$env:RESOURCE_GROUP="predoc_url"
$env:CONTAINER_NAME="predoc_url"
$env:DNS_NAME_LABEL="predoc-url"

#shell version
RESOURCE_GROUP="predoc_url"
CONTAINER_NAME="predoc-url"
DNS_NAME_LABEL="predoc-url-abc"
LOCATION="japaneast"
az group create --name $RESOURCE_GROUP --location $LOCATION
# run azure container instance with the image and .env file in region japaneast, run once only.

az container create --restart-policy Never --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --image radezheng/predoc_url --dns-name-label $DNS_NAME_LABEL --ports 80 --cpu 1 --memory 1 --location $LOCATION --environment-variables $(cat .env | xargs)


echo $(cat .env | xargs)
#get the log
az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME

#stream the log
az container attach --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME

#delete the container
az container delete --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --yes

#delete the resource group
az group delete --name $RESOURCE_GROUP


