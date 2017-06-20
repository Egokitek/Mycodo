#!/bin/bash

if [ "$EUID" -ne 0 ] ; then
    printf "Please run as root.\n"
    exit 1
fi

if [ ! -e $2 ]; then
    echo "Directory does not exist"
    exit 1
elif [ ! -d $2 ]; then
    echo "Input not a directory"
    exit 2
fi

INSTALL_DIRECTORY=$( cd -P /var/www/mycodo/.. && pwd -P )
echo '1' > ${INSTALL_DIRECTORY}/Mycodo/.restore

function error_found {
    echo '2' > ${INSTALL_DIRECTORY}/Mycodo/.restore
    exit 1
}

CURRENT_VERSION=$(python ${INSTALL_DIRECTORY}/Mycodo/mycodo/utils/github_release_info.py -c 2>&1)
NOW=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/var/Mycodo-backups/Mycodo-backup-${NOW}-${CURRENT_VERSION}"

printf "#### Restore of backup $2 initiated $NOW ####\n"

printf "#### Stopping Daemon and HTTP server ####\n"
service mycodo stop
/etc/init.d/apache2 stop

mkdir -p /var/Mycodo-backups

printf "\nBacking up current Mycodo from ${INSTALL_DIRECTORY}/Mycodo to ${BACKUP_DIR}..."
if ! mv ${INSTALL_DIRECTORY}/Mycodo ${BACKUP_DIR} ; then
    printf "Failed: Error while trying to back up current Mycodo install from ${INSTALL_DIRECTORY}/Mycodo to ${BACKUP_DIR}.\n"
    error_found
fi
printf "Done.\n"

printf "\nRestoring Mycodo from $2 to ${INSTALL_DIRECTORY}/Mycodo..."
if ! mv $2 ${INSTALL_DIRECTORY}/Mycodo ; then
    printf "Failed: Error while trying to restore Mycodo backup from ${INSTALL_DIRECTORY}/Mycodo to ${BACKUP_DIR}.\n"
    error_found
fi
printf "Done.\n"

if [ -d ${BACKUP_DIR}/env ] ; then
    printf "Moving env directory..."
    if ! mv ${BACKUP_DIR}/env ${INSTALL_DIRECTORY}/Mycodo ; then
        printf "Failed: Error while trying to move env directory.\n"
        error_found
    fi
    printf "Done.\n"
fi

if [ -d ${BACKUP_DIR}/cameras ] ; then
    printf "Moving cameras directory..."
    if ! mv ${BACKUP_DIR}/cameras ${INSTALL_DIRECTORY}/Mycodo/ ; then
        printf "Failed: Error while trying to move cameras directory.\n"
    fi
    printf "Done.\n"
fi

sleep 10

if ! ${INSTALL_DIRECTORY}/Mycodo/mycodo/scripts/upgrade_commands.sh initialize ; then
  printf "Failed: Error while running initialization script.\n"
  error_found
fi

printf "\n\nRunning post-restore script...\n"
if ! ${INSTALL_DIRECTORY}/Mycodo/mycodo/scripts/upgrade_post.sh ; then
  printf "Failed: Error while running post-restore script.\n"
  error_found
fi
printf "Done.\n\n"

date
printf "Restore completed successfully without errors.\n"
echo '0' > ${INSTALL_DIRECTORY}/Mycodo/.restore
