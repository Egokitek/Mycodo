#!/bin/bash
# Generates the API offline HTML documentation
#
# Dependencies
# sudo npm install -g redoc-cli
# sudo npm install -g npx
#

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
cd ${INSTALL_DIRECTORY}

if curl -k -s --head --request GET https://192.168.0.9/api/swagger.json | grep "200 OK" > /dev/null; then
  if [[ $(command -v redoc-cli) ]]
  then
    wget --no-check-certificate https://192.168.0.9/api/swagger.json ${INSTALL_DIRECTORY}/swagger.json
    npx redoc-cli bundle -o ${INSTALL_DIRECTORY}/mycodo-api.html ${INSTALL_DIRECTORY}/swagger.json
    rm -rf ${INSTALL_DIRECTORY}/swagger.json

    # Change title
    sed -i 's/<title>ReDoc documentation<\/title>/<title>Mycodo API documentation<\/title>/g' ${INSTALL_DIRECTORY}/mycodo-api.html

    cp ${INSTALL_DIRECTORY}/mycodo-api.html ${INSTALL_DIRECTORY}/mycodo/mycodo_flask/templates/mycodo-api.html
    cp ${INSTALL_DIRECTORY}/mycodo-api.html ${INSTALL_DIRECTORY}/docs/mycodo-api.html
  fi
else
  printf "Cannot connect to https://192.168.0.9/api/swagger.json\n"
fi
