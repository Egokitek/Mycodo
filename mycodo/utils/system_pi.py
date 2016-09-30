# coding=utf-8

import grp
import os
import pwd
import socket
import subprocess
import sys



def cmd_output(command, su_mycodo=True):
    """
    Executed command and returns a list of lines from the output
    """
    full_cmd = '{}'.format(command)
    if su_mycodo:
        full_cmd = 'su mycodo && {}'.format(command)
    cmd = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, shell=True)
    cmd_output, cmd_err = cmd.communicate()
    cmd_status = cmd.wait()
    return cmd_output, cmd_err, cmd_status


def get_git_commit():
    current_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    output, err, status = cmd_output('cd {} && git rev-parse --short HEAD'.format(current_path))
    return output[:7]


def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Checks if there is an internet connection
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception as ex:
        pass
    return False


def assure_path_exists(new_dir):
    """Create path if it doesn't exist"""
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)
        set_user_grp(new_dir, 'mycodo', 'mycodo')


def find_owner(filename):
    """Return the owner of a file"""
    return pwd.getpwuid(os.stat(filename).st_uid).pw_name


def get_sec(time_str):
    """Convert HH:MM:SS string into number of seconds"""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def set_user_grp(filepath, user, group):
    """Set the UID and GUID of a file"""
    uid = pwd.getpwnam(user).pw_uid
    gid = grp.getgrnam(group).gr_gid
    os.chown(filepath, uid, gid)
