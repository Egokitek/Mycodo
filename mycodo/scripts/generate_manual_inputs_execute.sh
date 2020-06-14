#!/bin/bash
# Generates the Inputs section of the Mycodo Manual
#

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
cd "${INSTALL_DIRECTORY}" || return

"${INSTALL_DIRECTORY}"/env/bin/python "${INSTALL_DIRECTORY}"/mycodo/scripts/generate_manual_inputs.py

awk '
    BEGIN       {p=1}
    /^.. BEGIN BUILT-IN INPUTS/   {print;system("cat '${INSTALL_DIRECTORY}'/mycodo-inputs.rst");p=0}
    /^.. END BUILT-IN INPUTS/     {p=1}
    p' "${INSTALL_DIRECTORY}"/mycodo-manual.rst > "${INSTALL_DIRECTORY}"/mycodo-manual_2.rst

mv "${INSTALL_DIRECTORY}"/mycodo-manual_2.rst "${INSTALL_DIRECTORY}"/mycodo-manual.rst

rm -rf "${INSTALL_DIRECTORY}"/mycodo-inputs.rst
