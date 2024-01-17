
docker build . -t radezheng/predoc_url 

#debug shell
docker run -it --env-file .env --rm radezheng/predoc_url pwsh


#run with env setting in .env file, delete the instance after running
docker run --env-file .env --rm radezheng/predoc_url


$env:RESOURCE_GROUP="predoc_url"
$env:CONTAINER_NAME="predoc_url"
$env:DNS_NAME_LABEL="predoc-url"

#shell version
RESOURCE_GROUP="predoc_url"
CONTAINER_NAME="predoc-url"
DNS_NAME_LABEL="predoc-url-111"
LOCATION="japaneast"
az group create --name $RESOURCE_GROUP --location $LOCATION
# run azure container instance with the image and .env file in region japaneast, run once only.

az container create --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --image radezheng/predoc_url --dns-name-label $DNS_NAME_LABEL --ports 80 --cpu 1 --memory 1 --location $LOCATION --environment-variables $(cat .env | xargs)


echo $(cat .env | xargs)
#get the log
az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME

#stream the log
az container attach --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME
