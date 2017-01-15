#include <linux/limits.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
	setuid(0);
	char cmd[255];

	if (argc > 1) {
		if (strcmp(argv[1], "start") == 0) {

			sprintf(cmd, "service mycodo start");
			system(cmd);

		} else if (strcmp(argv[1], "restart") == 0) {

			sprintf(cmd, "service mycodo restart");
			system(cmd);

		} else if (strcmp(argv[1], "debug") == 0) {

			sprintf(cmd, "service mycodo stop");
			system(cmd);
			sprintf(cmd, "/../mycodo_daemon.py -d");
			system(cmd);

		} else if (strcmp(argv[1], "delete-backup") == 0 && (argc > 2)) {

			sprintf(cmd, "rm -rf /var/Mycodo-backups/%s", argv[2]);
			system(cmd);

		} else if (strcmp(argv[1], "upgrade") == 0) {

			char updateScript[255];
			strncpy(updateScript, argv[0], sizeof(updateScript));
			dirname(updateScript);
			strncat(updateScript, "bash /upgrade_mycodo_release.sh upgrade", sizeof(updateScript));
			system(updateScript);

		}
	} else {

		printf("mycodo-wrapper: A wrapper to allow the mycodo web interface\n");
		printf("                to stop and start the daemon and update the\n");
		printf("                mycodo system to the latest version.\n\n");
		printf("Usage: mycodo-wrapper start|restart|debug|update|restore [commit]\n\n");
		printf("Options:\n");
		printf("   start:                  Start the mycodo daemon\n");
		printf("   restart:                Restart the mycodo daemon in normal mode\n");
		printf("   debug:                  Restart the mycodo daemon in debug mode\n");
		printf("   delete-backup [folder]: Delete Mycodo backup folder named [folder]\n");
		printf("   upgrade:                Upgrade Mycodo to the latest version on github\n");
	}

	return 0;
}
