## 5.0.31 (2017-05-31)

### Features

 - Add option to not turn wireless relay on or off at startup

### Bugfixes

 - Fix inability to save SHT sensor options (#251)
 - Fix inability to turn relay on if another relay is unconfigured (#251)

## 5.0.30 (2017-05-23)

### Bugfixes

 - Fix display of proper relay status if pin is 0

## 5.0.29 (2017-05-23)

### Features

 - Relay and Timer page style improvements

### Bugfixes

 - Add influxdb query generator with input checks

## 5.0.28 (2017-05-23)

### Features

  - Add support for Atlas Scientific pH Sensor ([#238](https://github.com/kizniche/mycodo/issues/238))
  - Add support for calibrating the Atlas Scientific pH sensor
  - Add UART support for Atlas Scientific PT-1000 sensor
  - Update Korean translations
  - Add measurement retries upon CRC fail for AM2315 sensor ([#246](https://github.com/kizniche/mycodo/issues/246))
  - Add page error handler that provides full traceback when the Web UI crashes
  - Display live pH measurements during pH sensor calibration
  - Add ability to clear calibration data from Atlas Scientific pH sensors
  - Add sensor option to calibrate Atlas Scientific pH sensor with the temperature from another sensor before measuring pH
  - Add 433MHz wireless transmitter/receiver support for relay actuation ([#88](https://github.com/kizniche/mycodo/issues/88), [#245](https://github.com/kizniche/mycodo/issues/245))

### Bugfixes

  - Fix saving of proper start time during timer creation ([#248](https://github.com/kizniche/mycodo/issues/248))
  - Fix unicode error when generating relay usage reports

## 5.0.27 (2017-04-12)

### Bugfixes

  - Fix issue with old database entries and new graph page parsing
  - Revert to old relay form submission method (ajax method broken)

## 5.0.26 (2017-04-12)

### Bugfixes

  - Fix critical issue with upgrade script

## 5.0.25 (2017-04-12)

### Bugfixes

  - Fix setting custom graph colors

## 5.0.24 (2017-04-12)

### Features

  - Add toastr and ajax support for submitting forms without refreshing the page (currently only used with relay On/Off/Duration buttons) ([#70](https://github.com/kizniche/mycodo/issues/70))

### Bugfixes

  - Fix issue with changing ownership of SSL certificates during install ([#240](https://github.com/kizniche/mycodo/issues/240))
  - Fix PID Output not appearing when adding new graph (modifying graph works)
  - Remove ineffective upgrade reversion script (reversion was risky)

## 5.0.23 (2017-04-10)

### Features

  - Add PID Output as a graph display option (useful for tuning PID controllers)

### Bugfixes

  - Fix display of unicode characters ([#237](https://github.com/kizniche/mycodo/issues/237))

## 5.0.22 (2017-04-08)

### Features

  - Add sensor conditional: emailing of photo or video (video only supported by picamera library at the moment) ([#226](https://github.com/kizniche/mycodo/issues/226))

### Bugfixes

  - Fix inability to display Sensor page if unable to detect DS18B20 sensors ([#236](https://github.com/kizniche/mycodo/issues/236))
  - Fix inability to disable relay during camera capture
  - Fix SSL generation script and strengthen from 2048 bit to 4096 bit RSA ([#234](https://github.com/kizniche/mycodo/issues/234))

### Miscellaneous

  - New cleaner Timer page style

## 5.0.21 (2017-04-02)

### Bugfixes

  - Fix BMP280 sensor module initialization ([#233](https://github.com/kizniche/mycodo/issues/233))
  - Fix saving and display of PID and Relay values on LCDs

## 5.0.20 (2017-04-02)

### Bugfixes

  - Fix BMP280 sensor module initialization
  - Fix saving and display of PID and Relay values on LCDs
  - Fix inability to select certain measurements for a sensor under the PID options

## 5.0.19 (2017-04-02)

### Bugfixes

  - Fix BMP280 sensor I<sup>2</sup>C address options ([#233](https://github.com/kizniche/mycodo/issues/233))

## 5.0.18 (2017-04-01)

### Features

  - Add BMP280 I2C temperature and pressure sensor ([#233](https://github.com/kizniche/mycodo/issues/233))

## 5.0.17 (2017-03-31)

### Bugfixes

  - Fix issue with graph page crashing when non-existent sensor referenced ([#232](https://github.com/kizniche/mycodo/issues/232))

## 5.0.16 (2017-03-30)

### Features

  - New Mycodo Manual rendered in markdown, html, pdf, and plain text

### Bugfixes

  - Fix BME280 sensor module to include calibration code (fixes "stuck" measurements)
  - Fix issue with graph page crashing when non-existent sensor referenced ([#231](https://github.com/kizniche/mycodo/issues/231))

## 5.0.15 (2017-03-28)

### Bugfixes

  - Fix issue with graph page errors when creating a graph with PIDs or Relays
  - Fix sensor conditional measurement selections ([#230](https://github.com/kizniche/mycodo/issues/230))
  - Fix inability to stream video from a Pi camera ([#228](https://github.com/kizniche/mycodo/issues/228))
  - Fix inability to delete LCD ([#229](https://github.com/kizniche/mycodo/issues/229))
  - Fix measurements export
  - Fix display of BMP and BH1750 sensor measurements in sensor lists (graphs/export)

### Miscellaneous

  - Better exception-handling (clean up logging of influxdb measurement errors)

## 5.0.14 (2017-03-25)

### Features

  - Add BH1750 I2C light sensor ([#224](https://github.com/kizniche/mycodo/issues/224))

### Bugfixes

  - Change default opencv values for new cameras ([#225](https://github.com/kizniche/mycodo/issues/225))
  - Fix relays not recording proper ON duration (which causes other issues) ([#223](https://github.com/kizniche/mycodo/issues/223))
  - Fix new graphs occupying 100% width (12/12 columns)

## 5.0.13 (2017-03-24)

### Bugfixes

  - Fix issue with adding/deleting relays
  - Fix inability to have multiple graphs appear on the same row
  - Fix UnicodeEncodeError when using translations
  - Fix BME280 sensor pressure/altitude

## 5.0.12 (2017-03-23)

### Bugfixes

  - Fix frontend and backend issues with conditionals

## 5.0.11 (2017-03-22)

### Bugfixes

  - Fix alembic database upgrade error (hopefully)

## 5.0.10 (2017-03-22)

### Bugfixes

  - Fix photos being taken uncontrollably when a time-lapse is active

## 5.0.9 (2017-03-22)

### Bugfixes

  - Update geocoder to 1.21.0 to attempt to resolve issue
  - Fix creation of alembic version number in database of new install
  - Add suffixes to distinguish Object from Die temperatures of TMP006 sensor on Live page
  - Fix reference to pybabel in virtualenv

## 5.0.8 (2017-03-22)

### Features

  - Add option to hide tooltips

### Bugfixes

  - Add alembic upgrade check as a part of flask app startup
  - Fix reference to alembic for database upgrades
  - Fix photos being taken uncontrollably when a time-lapse is active
  - Show edge measurements as vertical bars instead of lines on graphs
  - Fix default image width/height when adding cameras
  - Prevent attempting to setup a relay at startup if the GPIO pin is < 1
  - Add coverage where DHT22 sensor could be power cycled to fix an inability to acquire measurements
  - Display the device name next to each custom graph color
  - Fix encoding error when collecting anonymous statistics ([#216](https://github.com/kizniche/mycodo/issues/216))

### Miscellaneous

  - Update Influxdb to version 1.2.2
  - UI style improvements

## 5.0.7 (2017-03-19)

### Bugfixes

  - Fix pybabel reference during install/upgrade ([#212](https://github.com/kizniche/mycodo/issues/212))

## 5.0.6 (2017-03-19)

### Bugfixes

  -  Fix edge detection conditional statements ([#214](https://github.com/kizniche/mycodo/issues/214))
  -  Fix identification and conversion of dewpoint on live page ([#215](https://github.com/kizniche/mycodo/issues/215))

## 5.0.5 (2017-03-18)

### Bugfixes

  - Fix issue with timers not actuating relays ([#213](https://github.com/kizniche/mycodo/issues/213))

## 5.0.4 (2017-03-18)

### Bugfixes

  - Fix issues with saving LCD options ([#211](https://github.com/kizniche/mycodo/issues/211))

## 5.0.0 (2017-03-18)

### Bugfixes

  - Fixes inability of relay conditionals to operate ([#209](https://github.com/kizniche/mycodo/issues/209), [#210](https://github.com/kizniche/mycodo/issues/210))
  - Fix issue with user creation/deletion in web UI
  - Fix influxdb being unreachable directly after package install

### Features

  - Complete Spanish translation
  - Add auto-generation of relay usage/cost reports on a daily, weekly, or monthly schedule
  - Add ability to check daemon health (mycodo_client.py --checkdaemon)
  - Add sensor conditional actions: Activate/Deactivate PID, Email Photo, Email Video
  - Add PID option: maximum allowable sensor measurement age (to allow the PID controller to manipulate relays, the sensor measurement must have occurred in the past x seconds)
  - Add PID option: minimum off duration for lower/raise relay (protects devices that require a minimum off period by preventing power cycling from occurring too quickly)
  - Add new sensor: Free Disk Space (of a set path)
  - Add new sensor: Mycodo Daemon RAM Usage (used for testing)
  - Add ability to use multiple camera configurations (multiple cameras)
  - Add OpenCV camera library to allow use of USB cameras ([#193](https://github.com/kizniche/mycodo/issues/193))
  - Automatically detect DS18B20 sensors in sensor configuration
  - Add ability to create custom user roles
  - Add new user roles: Editor and Monitor ([#46](https://github.com/kizniche/mycodo/issues/46))

### Miscellaneous

  - Mobile display improvements
  - Improve content and accessibility of help documentation
  - Redesign navigation menu (including glyphs from bootstrap and fontawesome)
  - Move to using a Python virtual environment ([#203](https://github.com/kizniche/mycodo/issues/203))
  - Refactor the relay/sensor conditional management system
  - User names are no longer case-sensitive
  - Switch to using Flask-Login
  - Switch to using flask_wtf.FlaskForm (from using deprecated flask_wtf.Form)
  - Update web interface style and layout
  - Update influxdb to 1.2.1
  - Update Flask WTF to 0.14.2
  - Move from using sqlalchemy to flask sqlalchemy
  - Restructure database ([#115](https://github.com/kizniche/mycodo/issues/115), [#122](https://github.com/kizniche/mycodo/issues/122))

## 4.2.0 (2017-03-16)

### Features

  - Add ability to turn a relay on for a specific duration of time
  - Update style of Timer and Relay pages (mobile-compatibility)

## 4.1.16 (2017-02-05)

### Bugfixes

  - Revert back to influxdb 1.1.1 to fix LCD time display ([#7877](https://github.com/influxdata/influxdb/issues/7877) will fix, when released)
  - Fix influxdb not restarting after a new version is installed
  - Fix issue with relay conditionals being triggered upon shutdown
  - Fix asynchronous graph to use local timezone rather than UTC ([#185](https://github.com/kizniche/mycodo/issues/185))

### Miscellaneous

  - Remove archived versions of Mycodo (Mycodo/old) during upgrade (saves space during backup)

## 4.1.15 (2017-01-31)

### Bugfixes

  - Fix LCD KeyError from missing measurement unit for durations_sec

## 4.1.14 (2017-01-30)

### Bugfixes

  - Fix DHT11 sensor module ([#176](https://github.com/kizniche/mycodo/issues/176))

### Miscellaneous

  - Update influxdb to 1.2.0

## 4.1.13 (2017-01-30)

### Bugfixes

  - Fix DHT11 sensor module ([#176](https://github.com/kizniche/mycodo/issues/176))

## 4.1.12 (2017-01-30)

### Bugfixes

  - Fix PID controller crash

## 4.1.11 (2017-01-30)

This is a small update, mainly to fix the install script. It also *should* fix the DHT11 sensor module from stopping at the first bad checksum.

### Bugfixes

  - Fix DHT11 sensor module, removing exception preventing acquisition of future measurements ([#176](https://github.com/kizniche/mycodo/issues/176))
  - Fix setup.sh install script by adding git as a dependency ([#183](https://github.com/kizniche/mycodo/issues/183))
  - Fix initialization script executed during install and upgrade

## 4.1.10 (2017-01-29)

### Bugfixes

  - Fix PID variable initializations
  - Fix KeyError in controller_lcd.py
  - Fix camera termination bug ([#178](https://github.com/kizniche/mycodo/issues/178))
  - Fix inability to pause/hold/resume PID controllers

### Miscellaneous

  - Add help text for conditional statements to relay page ([#181](https://github.com/kizniche/mycodo/issues/181))

## 4.1.9 (2017-01-27)

This update fixes two major bugs: Sometimes admin users not being created properly from the web UI and the daemon not being set to automatically start during install.

This update also fixes an even more severe bug affecting the database upgrade system. If you installed a system before this upgrade, you are probably affected. This release will display a message indicating if your database has an issue. Deleting ~/Mycodo/databases/mycodo.db and restarting the web server (or reboot) will regenerate the database.

If your daemon doesn't automatically start because you installed it with a botched previous version, issue the following commands to add it to systemctl's autostart:

***Important***: Make sure you rename 'user' below to your actual user where you installed Mycodo, and make sure the Mycodo install directory is correct and points to the correct mycodo.service file.

```
sudo service mycodo stop
sudo systemctl disable mycodo.service
sudo rm -rf /etc/systemd/system/mycodo.service
sudo systemctl enable /home/user/Mycodo/install/mycodo.service
sudo service mycodo start
```

### Features

  - Add check for problematic database and notify user how to fix it
  - Add ability to define the colors of lines on general graphs ([#161](https://github.com/kizniche/mycodo/issues/161))

### Bugfixes

  - Update install instructions to correct downloading the latest release tarball
  - Fix for database upgrade bug that has been plaguing Mycodo for the past few releases
  - Fix incorrect displaying of graphs with relay or PID data
  - Fix relay turning off when saving relay settings and GPIO pin doesn't change
  - Fix bug that crashes the daemon if the user database is empty
  - Fix Spanish translation file errors
  - Fix mycodo daemon not automatically starting after install
  - Fix inability to create admin user from the web interface
  - Fix inability to delete methods
  - Fix Atlas PT100 sensor module 'invalid literal for float()' error
  - Fix camera termination bug ([#178](https://github.com/kizniche/mycodo/issues/178))

Miscellaneous

  - Add new theme: Sun

## 4.1.8 (2017-01-21)

### Bugfixes

  - Actually fix the upgrade system (mycodo_wrapper)
  - Fix bug in DHT22 sensor module preventing measurements
  - Fix inability to show latest time-lapse image on the camera page (images are still being captured)

### Miscellaneous

  - Update Spanish translations

## 4.1.7 (2017-01-19)

### Bugfixes

  - Fix upgrade system (mycodo_wrapper). This may have broke the upgrade system (if so, use the manual method in the README)
  - Fix time-lapses not resuming after an upgrade
  - Fix calculation of total 1-month relay usage and cost
  - Fix (and modify) the logging behavior in modules
  - Fix K30 sensor module returning None as a measurement value
  - Fix gpiod being added to crontab during install from setup.sh ([#174](https://github.com/kizniche/mycodo/issues/174))

## 4.1.6 (2017-01-17)

### Features

  - Add ability to export selected measurement data (in CSV format) from a date/time span

### Bugfixes

  - Fix issue with setup.sh when the version of wget<1.16 ([#173](https://github.com/kizniche/mycodo/issues/173))
  - Fix error calculating rely usage when it's currently the billing day of the month

### Miscellaneous

  - Remove Sensor Logs (Tools/Sensor Logs). The addition of the measurement export feature in this release deprecates Sensor Logs. Note that by the very nature of how the Sensor Log controllers were designed, there was a high probability of missing measurements. The new measurement export feature ensures all measurements are exported.
  - Add more translatable text
  - Add password repeat input when creating new admin user

## 4.1.5 (2017-01-14)

### Bugfixes

  - Fix DHT11 sensor module not returning values ([#171](https://github.com/kizniche/mycodo/issues/171))
  - Fix HTU21D sensor module not returning values ([#172](https://github.com/kizniche/mycodo/issues/172))

## 4.1.4 (2017-01-13)

This release introduces a new method for upgrading Mycodo to the latest version. Upgrades will now be performed from github releases instead of commits, which should prevent unintended upgrades to the public, facilitate bug-tracking, and enable easier management of a changelog.

### Performance

  - Add ability to hold, pause and resume PID controllers
  - Add ability to modify PID controller parameters while active, held, or paused
  - New method of processing data on live graphs that is more accurate and reduced bandwidth
  - Install numpy binary from apt instead of compiling with pip

### Features

  - Add ability to set the language of the web user interface ([#167](https://github.com/kizniche/mycodo/issues/167))
  - Add Spanish language translation
  - New upgrade system to perform upgrades from github releases instead of commits
  - Allow symbols to be used in a user password ([#76](https://github.com/kizniche/mycodo/issues/76))
  - Introduce changelog (CHANGELOG.md)

### Bugfixes

  - Fix inability to update long-duration relay times on live graphs
  - Fix dew point being incorrectly inserted into the database
  - Fix inability to start video stream ([#155](https://github.com/kizniche/mycodo/issues/155))
  - Fix SHT1x7x sensor module not returning values ([#159](https://github.com/kizniche/mycodo/issues/159))

### Miscellaneous

  - Add more software tests
  - Update Flask to v0.12
  - Update InfluxDB to v1.1.1
  - Update factory_boy to v2.8.1
  - Update sht_sensor to v16.12.1
  - Move install files to Mycodo/install

## 4.0.26 (2016-11-23)

### Features

  - Add more I2C LCD address options (again)
  - Add Fahrenheit conversion for temperatures on /live page
  - Add github issue template ([#150](https://github.com/kizniche/mycodo/issues/150) [#151](https://github.com/kizniche/Mycodo/pull/151))
  - Add information to the README about performing manual backup/restore
  - Add universal sensor tests

### Bugfixes

  - Fix code warnings and errors
  - Add exceptions, logging, and docstrings

## 4.0.25 (2016-11-13)

### Features

  - New create admin user page if no admin user exists
  - Add support for [Chirp soil moisture sensor](https://wemakethings.net/chirp/)
  - Add more I2C LCD address options
  - Add endpoint tests
  - Add use of [Travis CI](https://travis-ci.org/) and [Codacy](https://www.codacy.com/)

### Bugfixes

  - Fix controller crash when using a 20x4 LCD ([#136](https://github.com/kizniche/mycodo/issues/136))
  - Add short sleep() to login to reduce chance of brute-force success
  - Fix code warnings and errors

## 4.0.24 (2016-10-26)

### Features

  - Setup flask app using new create_app() factory
  - Create application factory and moved view implementation into a general blueprint ([#129](https://github.com/kizniche/mycodo/issues/129) [#132](https://github.com/kizniche/Mycodo/pull/132) [#142](https://github.com/kizniche/Mycodo/pull/142))
  - Add initial fixture tests

## 4.0.23 (2016-10-18)

### Performance

  - Improve time-lapse capture method

### Features

  - Add BME280 sensor
  - Create basic tests for flask app ([#112](https://github.com/kizniche/mycodo/issues/122))
  - Relocated Flask UI into its own package ([#116](https://github.com/kizniche/Mycodo/pull/116))
  - Add DB session fixtures; create model factories
  - Add logging of relay durations that are turned on and off, without a known duration
  - Add ability to define power billing cycle day, AC voltage, cost per kWh, and currency unit for relay usage statistics
  - Add more Themes
  - Add hostname to UI page title

### Bugfixes

  - Fix relay conditionals when relays turn on for durations of time ([#123](https://github.com/kizniche/mycodo/issues/123))
  - Exclude photo/video directories from being backed up during upgrade
  - Removed unused imports
  - Changed print statements to logging statements
  - Fix inability to save sensor settings ([#120](https://github.com/kizniche/mycodo/issues/120) [#134](https://github.com/kizniche/mycodo/issues/134))
