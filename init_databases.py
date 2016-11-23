#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  init_databases.py - Create and update Mycodo SQLite databases
#
#  Copyright (C) 2015  Kyle T. Gabriel
#
#  This file is part of Mycodo
#
#  Mycodo is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Mycodo is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Mycodo. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at kylegabriel.com

import argparse
import getpass
import logging
import os
import sys
import errno

import sqlalchemy

from mycodo.config import SQL_DATABASE_USER, SQL_DATABASE_NOTE, SQL_DATABASE_MYCODO
from mycodo.databases.users_db.models import Users
from mycodo.databases.utils import session_scope
from mycodo.scripts.utils import test_username, test_password, is_email, query_yes_no

if sys.version[0] == "3":
    raw_input = input  # Make sure this works in PY3

USER_DB_PATH = 'sqlite:///' + SQL_DATABASE_USER
MYCODO_DB_PATH = 'sqlite:///' + SQL_DATABASE_MYCODO
NOTES_DB_PATH = 'sqlite:///' + SQL_DATABASE_NOTE


def add_user(admin=False):
    new_user = Users()

    print('\nAdd user to database')

    while True:
        user_name = raw_input('User (a-z, A-Z, 2-64 chars): ')
        if test_username(user_name):
            new_user.user_name = user_name
            break

    while True:
        user_password = getpass.getpass('Password: ')
        user_password_again = getpass.getpass('Password (again): ')
        if user_password != user_password_again:
            print("Passwords don't match")
        else:
            if test_password(user_password):
                new_user.set_password(user_password)
                break

    while True:
        user_email = raw_input('Email: ')
        if is_email(user_email):
            new_user.user_email = user_email
            break

    if admin:
        new_user.user_restriction = 'admin'
    else:
        new_user.user_restriction = 'guest'

    new_user.user_theme = 'slate'
    try:
        with session_scope(USER_DB_PATH) as db_session:
            db_session.add(new_user)
        sys.exit(0)
    except sqlalchemy.exc.OperationalError:
        print("Failed to create user.  You most likely need to "
              "create the DB before trying to create users.")
        sys.exit(1)
    except sqlalchemy.exc.IntegrityError:
        print("Username already exists.")
        sys.exit(1)


def delete_user(username):
    if query_yes_no("Confirm delete user '{}' from user database.".format(username)):
        try:
            with session_scope(USER_DB_PATH) as db_session:
                user = db_session.query(Users).filter(Users.user_name == username).one()
                db_session.delete(user)
                print("User deleted.")
                sys.exit(0)
        except sqlalchemy.orm.exc.NoResultFound:
            print("No user found with this name.")
            sys.exit(1)


def change_password(username):
    print('Changing password for {}'.format(username))

    with session_scope(USER_DB_PATH) as db_session:
        user = db_session.query(Users).filter(Users.user_name == username).one()

        while True:
            user_password = getpass.getpass('Password: ')
            user_password_again = getpass.getpass('Password (again): ')
            if user_password != user_password_again:
                print("Passwords don't match")
            else:
                try:
                    if test_password(user_password):
                        user.set_password(user_password)
                        sys.exit(0)
                except sqlalchemy.orm.exc.NoResultFound:
                    print("No user found with this name.")
                    sys.exit(1)


def create_dbs(db_name, create_all=False, config=None, exit_when_done=True):
    """
    Creates the individual databases using a database URI or
    a configuration object (like 'ProdConfig', or 'TestConfig' in
    mycodo.config

    :param db_name:  SQLAlchemy URI
    :param create_all: Bool to create all DBs
    :param config: Configuration Object to use custom URIs
    :param exit_when_done: Normally this code exits after setup is complete

    :return: None
    """
    user_db_path = config.SQL_DATABASE_USER if config and hasattr(config, 'SQL_DATABASE_USER') else SQL_DATABASE_USER
    mycodo_db_uri = config.MYCODO_DB_PATH if config and hasattr(config, 'MYCODO_DB_PATH') else MYCODO_DB_PATH
    notes_db_uri = config.NOTES_DB_PATH if config and hasattr(config, 'NOTES_DB_PATH') else NOTES_DB_PATH
    user_db_uri = config.USER_DB_PATH if config and hasattr(config, 'USER_DB_PATH') else USER_DB_PATH

    if not os.path.exists(os.path.dirname(user_db_path)):
        try:
            os.makedirs(os.path.dirname(user_db_path))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    if db_name == 'mycodo' or create_all:
        logging.debug("Creating/verifying mycodo.db at {} ...".format(mycodo_db_uri))

        from mycodo.databases.mycodo_db import init_db
        from mycodo.databases.mycodo_db import populate_db
        init_db(mycodo_db_uri)
        populate_db(mycodo_db_uri)

    if db_name == 'notes' or create_all:
        logging.debug("Creating/verifying notes.db at {} ...".format(notes_db_uri))

        from mycodo.databases.notes_db import init_db
        init_db(notes_db_uri)

    if db_name == 'users' or create_all:
        logging.debug("Creating/verifying users.db at {} ...".format(user_db_uri))

        from mycodo.databases.users_db import init_db
        init_db(user_db_uri)

    if exit_when_done:
        sys.exit(0)


def menu():
    parser = argparse.ArgumentParser(description="Initialize Mycodo Database "
                                                 "structure and manage users")

    parser.add_argument('-i', '--install_db', type=str,
                        choices=['users', 'mycodo', 'notes', 'all'],
                        help="Create new users.db, mycodo.db and/or note.db")

    parser.add_argument('-A', '--addadmin', action='store_true',
                        help="Add admin user to users database")

    parser.add_argument('-a', '--adduser', action='store_true',
                        help="Add user to users database")

    parser.add_argument('-d', '--deleteuser',
                        help="Remove user from users database")

    parser.add_argument('-p', '--pwchange',
                        help="Create a new password for user")

    args = parser.parse_args()

    if args.adduser:
        add_user()

    if args.addadmin:
        add_user(admin=True)

    if args.install_db:
        if args.install_db == 'all':
            create_dbs('', create_all=True)
        else:
            create_dbs(args.install_db)

    if args.deleteuser:
        delete_user(args.deleteuser)

    if args.pwchange:
        change_password(args.pwchange)


if __name__ == "__main__":
    menu()
