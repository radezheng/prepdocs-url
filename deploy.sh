
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
CONTAINER_NAME="predoc_url"
DNS_NAME_LABEL="predoc-url-111"

# run azure container instance with the image and .env file in region japaneast
az container create --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --image radezheng/predoc_url --dns-name-label $DNS_NAME_LABEL --ports 80 --cpu 1 --memory 1 --location japaneast --environment-variables $(cat .env | xargs)