#!/bin/bash

if [ "$EUID" -ne 0 ] ; then
    printf "Please run as root.\n"
    exit 1
fi

INSTALL_DIRECTORY=$( cd -P /var/www/mycodo/.. && pwd -P )

function error_found {
    exit 1
}

CURRENT_VERSION=$(python ${INSTALL_DIRECTORY}/Mycodo/mycodo/utils/github_release_info.py -c 2>&1)
NOW=$(date +"%Y-%m-%d_%H-%M-%S")
TMP_DIR="/var/tmp/Mycodo-backup-${NOW}-${CURRENT_VERSION}"
BACKUP_DIR="/var/Mycodo-backups/Mycodo-backup-${NOW}-${CURRENT_VERSION}"

printf "#### Create backup $2 initiated $NOW ####\n"

mkdir -p /var/Mycodo-backups

printf "Backing up current Mycodo from ${INSTALL_DIRECTORY}/Mycodo to ${TMP_DIR}..."
if ! rsync -avq --exclude=cameras --exclude=env --exclude=old ${INSTALL_DIRECTORY}/Mycodo ${TMP_DIR} ; then
    printf "Failed: Error while trying to back up current Mycodo install from ${INSTALL_DIRECTORY}/Mycodo to ${BACKUP_DIR}.\n"
    error_found
fi
printf "Done.\n"

printf "Moving ${TMP_DIR}/Mycodo to ${BACKUP_DIR}..."
if ! mv ${TMP_DIR}/Mycodo ${BACKUP_DIR} ; then
    printf "Failed: Error while trying to move ${TMP_DIR}/Mycodo to ${BACKUP_DIR}.\n"
    error_found
fi
printf "Done.\n"

date
printf "Backup completed successfully without errors.\n"
