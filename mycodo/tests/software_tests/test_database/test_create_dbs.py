# coding=utf-8
""" evaluates the create_dbs function """
#  Hardware specific libs are found through out the flask app pages
#  and the following mock work will patch them so that we can pretend
#  that we have them installed:
from mock import patch, MagicMock
patch.dict("sys.modules", RPi=MagicMock(), picamera=MagicMock()).start()

import os
from mycodo.tests.software_tests.conftest import uri_to_path
from init_databases import create_dbs


def test_create_dbs_mycodo_db(db_config):
    """ only create the mycodo_db """
    # Expect DB to exist
    create_dbs(config=db_config, exit_when_done=False)
    assert os.path.isfile(uri_to_path(db_config.MYCODO_DB_PATH)), "Mycodo Database File does not exist"
    assert os.path.getsize(uri_to_path(db_config.MYCODO_DB_PATH)) > 0, "Mycodo Database File was not set up (It is empty)"
