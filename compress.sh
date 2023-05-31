#!/bin/bash

version="0-0-2"

zipFile="bubbaAI-${version}.zip"

# directories=(
#     ""
# )

files=(
    "zips/bubba_ai-latest.tar"
    "Dockerrun.aws.json"
)

mkdir ./zips

zip -r "zips/$zipFile" "${directories[@]}" "${files[@]}"