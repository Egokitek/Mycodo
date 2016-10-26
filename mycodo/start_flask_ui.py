# coding=utf-8
""" Starts the mycodo flask UI """
import os
import argparse
from mycodo.mycodo_flask.app import create_app

app = create_app()  # required by the wsgi config and main()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Mycodo Flask HTTP server.",
                                     formatter_class=argparse.RawTextHelpFormatter)

    options = parser.add_argument_group('Options')
    options.add_argument('-d', '--debug', action='store_true',
                         help="Run Flask with debug=True (Default: False)")
    options.add_argument('-s', '--ssl', action='store_true',
                         help="Run Flask without SSL (Default: Enabled)")

    args = parser.parse_args()

    if args.debug:
        debug = True
    else:
        debug = False

    if args.ssl:
        app.run(host='0.0.0.0', port=80, debug=debug)
    else:
        # locate ssl certificates, if not executing Flask script from
        # the script's directory.
        file_path = os.path.abspath(__file__)
        dir_path = os.path.dirname(file_path)
        cert = os.path.join(dir_path, "mycodo_flask/ssl_certs/cert.pem")
        privkey = os.path.join(dir_path, "mycodo_flask/ssl_certs/privkey.pem")
        # chain = os.path.join(dir_path, "ssl_certs/chain.pem")
        context = (cert, privkey)
        app.run(host='0.0.0.0', port=443, ssl_context=context, debug=debug)
