#!/usr/bin/env bash

IMG='glasslabs/compass-bot'
VER='0.1'

# if docker build --rm --tag $IMG:$VER \
#     --build-arg discord_token=$DSC_API_TOKEN \
#     --build-arg discord_token_dev=$DSC_DEV_TOKEN \
#     --build-arg gitlab_token=$GITLAB_TOKEN \
#     --build-arg mongo_url=$MONGO_URL \
#     --build-arg spotify_id=$SPOTIFY_ID \
#     --build-arg spotify_secret=$SPOTIFY_SECRET \
#     -f Dockerfile . ;
# then
#   echo -e "\e[69mGREAT SUCCESS!\e[0m"  
#   docker push $IMG:$VER
# else 
#   echo -e "\e[31mERROR\e[0m: Docker build failed!"
#   exit
# fi

if docker build --tag $IMG:$VER \
    --build-arg discord_token=$DSC_API_TOKEN \
    --build-arg discord_token_dev=$DSC_DEV_TOKEN \
    --build-arg gitlab_token=$GITLAB_TOKEN \
    --build-arg mongo_url=$MONGO_URL \
    --build-arg spotify_id=$SPOTIFY_ID \
    --build-arg spotify_secret=$SPOTIFY_SECRET \
    -f Dockerfile . ;
then
  echo -e "\e[69mGREAT SUCCESS!\e[0m"  
else 
  echo -e "\e[31mERROR\e[0m: Docker build failed!"
  exit
fi
