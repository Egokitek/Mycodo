#!/bin/bash
#
#  setup.sh - Mycodo install script
#
#  Usage: sudo /bin/bash ~/Mycodo/install/setup.sh
#

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd -P )
INSTALL_CMD="/bin/bash ${INSTALL_DIRECTORY}/mycodo/scripts/upgrade_commands.sh"
INSTALL_DEP="/bin/bash ${INSTALL_DIRECTORY}/mycodo/scripts/dependencies.sh"
LOG_LOCATION=${INSTALL_DIRECTORY}/install/setup.log
INSTALL_TYPE="Full"

if [ "$EUID" -ne 0 ]; then
    printf "Please run as root: \"sudo /bin/bash ${INSTALL_DIRECTORY}/install/setup.sh\"\n";
    exit
fi

WHIPTAIL=$(command -v whiptail)
exitstatus=$?
if [ $exitstatus != 0 ]; then
    printf "\nwhiptail not installed. Install it with 'sudo apt-get install whiptail' then try the install again.\n"
    exit 1
fi

NOW=$(date)
printf "### Mycodo installation initiated $NOW\n" 2>&1 | tee -a ${LOG_LOCATION}

clear
LICENSE=$(whiptail --title "Mycodo Installer: License Agreement" \
                   --backtitle "Mycodo" \
                   --yesno "Mycodo is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.\n\nMycodo is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along with Mycodo. If not, see gnu.org/licenses\n\nDo you agree to the license terms?" \
                   20 68 \
                   3>&1 1>&2 2>&3)

exitstatus=$?
if [ $exitstatus != 0 ]; then
    echo "Mycodo install canceled by user" 2>&1 | tee -a ${LOG_LOCATION}
    exit
fi

clear
INSTALL_TYPE=$(whiptail --title "Mycodo Installer: Install Type" \
                        --backtitle "Mycodo" \
                        --notags \
                        --menu "\nSelect the Install Type:\n\nFull: Install all dependencies\nMinimal: Install a minimal set of dependencies\nCustom: Select which dependencies to install\n\nIf unsure, choose 'Full Install'" \
                        20 68 3 \
                        "full" "Full Install (recommended)" \
                        "minimal" "Minimal Install" \
                        "custom" "Custom Install" \
                        3>&1 1>&2 2>&3)
exitstatus=$?
if [ $exitstatus != 0 ]; then
    echo "Mycodo install canceled by user" 2>&1 | tee -a ${LOG_LOCATION}
    exit
fi
printf "\nInstall Type: $INSTALL_TYPE\n" >>${LOG_LOCATION} 2>&1

if [ "$INSTALL_TYPE" == "custom" ]; then
    clear
    DEP_STATUS=$(whiptail --title "Mycodo Install: Custom" \
                          --backtitle "Mycodo" \
                          --notags \
                          --checklist "Dependencies to Install" \
                          20 68 13 \
                          'Adafruit_ADS1x15' "Adafruit_ADS1x15" off \
                          'Adafruit_BME280' "Adafruit_BME280" off \
                          'Adafruit_BMP' "Adafruit_BMP" off \
                          'Adafruit_GPIO' "Adafruit_GPIO" off \
                          'Adafruit_MCP3008' "Adafruit_MCP3008" off \
                          'Adafruit_TMP' "Adafruit_TMP" off \
                          'MCP342x' "MCP342x" off \
                          'pigpio' "pigpio" off \
                          'quick2wire' "quick2wire" off \
                          'sht_sensor' "sht_sensor" off \
                          'tsl2561' "tsl2561" off \
                          'tsl2591' "tsl2591" off \
                          'w1thermsensor' "w1thermsensor" off \
                          3>&1 1>&2 2>&3)
    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        echo "Mycodo install canceled by user" 2>&1 | tee -a ${LOG_LOCATION}
        exit
    fi
fi

abort()
{
    printf "
************************************
** ERROR: Mycodo Install Aborted! **
************************************

An error occurred that may have prevented Mycodo from
being installed properly!

Open to the end of the setup log to view the full error:
${INSTALL_DIRECTORY}/install/setup.log

Please contact the developer by submitting a bug report
at https://github.com/kizniche/Mycodo/issues with the
pertinent excerpts from the setup log located at:
${INSTALL_DIRECTORY}/install/setup.log
" 2>&1 | tee -a ${LOG_LOCATION}
    exit 1
}

trap 'abort' 0

set -e

TOTAL=26  # The total number of times progress() called
COUNT=1

function progress() {
    echo -e "XXX\n$(awk "BEGIN { pc=100*${COUNT}/${TOTAL}; i=int(pc); print (pc-i<0.5)?i:i+1 }")\n${1}...\nXXX"
    ((COUNT++))
}

{
    progress "Sit back"
    sleep 4
    progress "Or grab a coffee"
    sleep 4
    progress "This may take a while"
    sleep 4

    SECONDS=0
    NOW=$(date)
    printf "#### Mycodo installation began $NOW\n" 2>&1 | tee -a ${LOG_LOCATION}

    progress "Checking swap size"
    ${INSTALL_CMD} update-swap-size >>${LOG_LOCATION} 2>&1

    progress "Updating apt sources"
    ${INSTALL_CMD} update-apt >>${LOG_LOCATION} 2>&1

    progress "Removing apt version of pip"
    ${INSTALL_CMD} uninstall-apt-pip >>${LOG_LOCATION} 2>&1

    progress "Installing apt dependencies"
    ${INSTALL_CMD} update-packages >>${LOG_LOCATION} 2>&1

    progress "Setting up virtualenv"
    ${INSTALL_CMD} setup-virtualenv >>${LOG_LOCATION} 2>&1

    progress "Updating virtualenv pip"
    ${INSTALL_CMD} update-pip3 >>${LOG_LOCATION} 2>&1

    progress "Installing WiringPi"
    ${INSTALL_CMD} update-wiringpi >>${LOG_LOCATION} 2>&1

    progress "Installing base python packages in virtualenv"
    ${INSTALL_CMD} update-pip3-packages >>${LOG_LOCATION} 2>&1

    progress "Setting up files and folders"
    ${INSTALL_CMD} initialize >>${LOG_LOCATION} 2>&1

    if [ "$INSTALL_TYPE" == "minimal" ]; then
        printf '\n#### Minimal install selected. No more dependencies to install.' >>${LOG_LOCATION} 2>&1
    elif [ "$INSTALL_TYPE" == "custom" ]; then
        printf '\n#### Installing custom-selected dependencies' >>${LOG_LOCATION} 2>&1
        progress "Installing custom python packages in virtualenv"
        for option in $DEP_STATUS
        do
            option="${option%\"}"
            option="${option#\"}"
            if [ "$option" == "Adafruit_ADS1x15" ]; then
                ${INSTALL_DEP} Adafruit_ADS1x15 >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "Adafruit_Python_BME280" ]; then
                ${INSTALL_DEP} Adafruit_Python_BME280 >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "Adafruit_BMP" ]; then
                ${INSTALL_DEP} Adafruit_BMP >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "Adafruit_GPIO" ]; then
                ${INSTALL_DEP} Adafruit_GPIO >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "Adafruit_MCP3008" ]; then
                ${INSTALL_DEP} Adafruit_MCP3008 >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "Adafruit_TMP" ]; then
                ${INSTALL_DEP} Adafruit_TMP >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "MCP342x" ]; then
                ${INSTALL_DEP} MCP342x >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "pigpio" ]; then
                ${INSTALL_DEP} install-pigpiod >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "quick2wire" ]; then
                ${INSTALL_DEP} quick2wire >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "sht_sensor" ]; then
                ${INSTALL_DEP} sht_sensor >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "tsl2561" ]; then
                ${INSTALL_DEP} tsl2561 >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "tsl2591" ]; then
                ${INSTALL_DEP} tsl2591 >>${LOG_LOCATION} 2>&1
            elif [ "$option" == "w1thermsensor" ]; then
                ${INSTALL_DEP} w1thermsensor >>${LOG_LOCATION} 2>&1
            fi
        done
        ${INSTALL_CMD} update-permissions >>${LOG_LOCATION} 2>&1
    elif [ "$INSTALL_TYPE" == "full" ]; then
        ${INSTALL_DEP} Adafruit_ADS1x15 >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} Adafruit_BMP >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} Adafruit_Python_BME280 >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} Adafruit_GPIO >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} Adafruit_MCP3008 >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} Adafruit_TMP >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} MCP342x >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} install-pigpiod >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} quick2wire >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} sht_sensor >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} tsl2561 >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} tsl2591 >>${LOG_LOCATION} 2>&1
        ${INSTALL_DEP} w1thermsensor >>${LOG_LOCATION} 2>&1
        ${INSTALL_CMD} update-permissions >>${LOG_LOCATION} 2>&1
    fi

    progress "Installing InfluxDB"
    ${INSTALL_CMD} update-influxdb >>${LOG_LOCATION} 2>&1

    progress "Setting up InfluxDB database and user"
    ${INSTALL_CMD} update-influxdb-db-user >>${LOG_LOCATION} 2>&1

    progress "Setting up logrotate"
    ${INSTALL_CMD} update-logrotate >>${LOG_LOCATION} 2>&1

    progress "Generating SSL certificate"
    ${INSTALL_CMD} ssl-certs-generate >>${LOG_LOCATION} 2>&1

    progress "Installing Mycodo startup script"
    ${INSTALL_CMD} update-mycodo-startup-script >>${LOG_LOCATION} 2>&1

    progress "Compiling translations"
    ${INSTALL_CMD} compile-translations >>${LOG_LOCATION} 2>&1

    progress "Updating cron"
    ${INSTALL_CMD} update-cron >>${LOG_LOCATION} 2>&1

    progress "Running initialization"
    ${INSTALL_CMD} initialize >>${LOG_LOCATION} 2>&1

    progress "Setting up the web server"
    ${INSTALL_CMD} web-server-update >>${LOG_LOCATION} 2>&1

    progress "Starting the web server"
    ${INSTALL_CMD} web-server-restart >>${LOG_LOCATION} 2>&1

    progress "Creating Mycodo database"
    ${INSTALL_CMD} web-server-connect >>${LOG_LOCATION} 2>&1

    progress "Setting permissions"
    ${INSTALL_CMD} update-permissions >>${LOG_LOCATION} 2>&1

    progress "Starting the Mycodo daemon"
    ${INSTALL_CMD} restart-daemon >>${LOG_LOCATION} 2>&1

} | whiptail --gauge "Installing Mycodo. Please wait..." 6 55 0

trap : 0

IP=$(ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/')

if [[ -z ${IP} ]]; then
  IP="your.IP.address.here"
fi

CURRENT_DATE=$(date)
printf "#### Mycodo Installer finished ${CURRENT_DATE}\n" 2>&1 | tee -a ${LOG_LOCATION}

DURATION=$SECONDS
printf "#### Total install time: $(($DURATION / 60)) minutes and $(($DURATION % 60)) seconds\n" 2>&1 | tee -a ${LOG_LOCATION}

printf "
************************************
** Mycodo successfully installed! **
************************************

The full install log is located at:
${INSTALL_DIRECTORY}/install/setup.log

Go to https://${IP}/, or whatever your Raspberry Pi's
IP address is, to create an admin user and log in.
" 2>&1 | tee -a ${LOG_LOCATION}
