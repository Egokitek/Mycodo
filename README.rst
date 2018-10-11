Mycodo
======

Environmental Regulation System

Latest version: 6.4.0 |Build Status| |Codacy Badge| |DOI|

`Mycodo Manual <https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.rst>`__
(`PDF <https://github.com/kizniche/Mycodo/raw/master/mycodo-manual.pdf>`__,
`HTML <http://htmlpreview.github.io/?https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.html>`__,
`TEXT <https://raw.githubusercontent.com/kizniche/Mycodo/master/mycodo-manual.txt>`__)

`Mycodo Wiki <https://github.com/kizniche/Mycodo/wiki>`__

Mycodo is an automated monitoring and regulation system that was built
to run on the `Raspberry
Pi <https://en.wikipedia.org/wiki/Raspberry_Pi>`__ (versions Zero, 1, 2,
and 3).

Originally designed to cultivate edible mushrooms, Mycodo has grown to
include the ability to do much more, including cultivating plants,
culturing microorganisms, maintaining honey bee apiary homeostasis,
incubating animals and eggs, maintaining aquatic systems, aging cheeses,
fermenting foods and tobacco, cooking food (sous-vide), and more.

The system comprises a backend (daemon) and a frontend (user interface).
The backend conducts measurements from sensors and devices, then
coordinate a diverse set of responses to those measurements, including
the ability to modulate outputs (relays, PWM, wireless outlets),
regulate environmental conditions with electrical devices under PID
control (steady regulation or changing over time), schedule timers,
capture photos and stream video, trigger actions when measurements meet
certain conditions (modulate relays, execute commands, notify by email,
etc.), and more. The frontend is a web interface that enables easy
navigation and configuration from any browser-enabled device.

.. contents::
   :depth: 3


What is PID Control?
--------------------

A `proportional-derivative-integral (PID)
controller <https://en.wikipedia.org/wiki/PID_controller>`__ is a
control loop feedback mechanism used throughout industry for controlling
systems. It efficiently brings a measurable condition, such as
temperature, to a desired state (setpoint). A well-tuned PID controller
can raise to a setpoint quickly, have minimal overshoot, and maintain
the setpoint with little oscillation.

.. figure:: manual_images/PID-animation.gif
   :alt: PID Animation


|Mycodo|

The top graph visualizes the regulation of temperature. The red line is
the desired temperature (setpoint) that has been configured to change
over the course of each day. The blue line is the actual recorded
temperature. The green vertical bars represent how long a heater has
been activated for every 20-second period. This regulation was achieved
with minimal tuning, and already displays a very minimal deviation from
the setpoint (±0.5° Celsius). Further tuning would reduce this
variability further.

Software Features
-----------------

-  Inputs: Periodically measure devices, such as analog-to-digital
   converters (ADCs), sensors (temperature, humidity, etc.), or add your
   own.
-  Outputs: Manipulate the environment by switching GPIO pins High or
   Low, switching relays, generating PWM signals, email notifications,
   executing linux commands, and more.
-  PID Controllers: Couple inputs with outputs to create feedback loops
   in order to regulate environmental conditions.
-  Methods: Change the desired condition over time (useful for reflow
   ovens, thermal cyclers, mimicking natural environmental changes,
   etc.)
-  Timers: Schedule the execution of actions at various times and
   intervals.
-  LCDs: Display measurements and data on 16x2 and 20x4 I2C-enabled LCD
   displays.
-  I2C Multiplexer Support: Allow multiple devices/sensors with the same
   I2C address to be used simultaneously.
-  Camera support: Raspberry Pi Camera and USB cameras, to stream live
   video (only Pi cam), capture still images and video, and create
   time-lapses.
-  Web Interface: Access using a web browser on your local network or
   anywhere in the world with an internet connection.
-  Secure Login: High-security login system utilizing the latest
   encryption and authorization standards.
-  System upgrade: When a new version is released on github, an upgrade
   can be initiated from the web interface.
-  Languages: English, `Español (Spanish) <#espa%C3%B1ol-spanish>`__,
   `Deutsche (German) <#deutsche-german>`__,
   `Français (French) <#fran%C3%A7ais-french>`__,
   `Italian <#italian>`__,
   `Portuguese <#portuguese>`__,
   `Russian <#russian>`__, and
   `Chinese <#chinese>`__ (Change
   language under Configure -> Language)

`Read the manual <#manual>`__ for details.

Supported Inputs
----------------

All supported Inputs can be found under `Sensor
Interfaces <https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.rst#sensor-interfaces>`__
and `Device
Setup <https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.rst#device-setup>`__.

Install
-------

These install procedures have been tested to work with the Raspberry Pi
(versions Zero, 1, 2, and 3) following a fresh install of
`Raspbian <https://www.raspberrypi.org/downloads/raspbian/>`__ (Full or
Lite version), with an active internet connection.

Once Raspbian has been installed, follow the guide below to set up the
system prior to installing Mycodo.

Configure raspi-config
~~~~~~~~~~~~~~~~~~~~~~

**It's very important that you don't skip the file system expansion and
reboot steps! These need to be done before continuing or there won't be
enough free disk space to install Mycodo.**

After writing Raspbian to an SD card and enabling ssh by creating a file
named ``ssh`` on the boot partition, insert the SD card into the Pi and
power the system. Whether you log in with the GUI or terminal via SSH to
your Raspberry Pi's IP address for the first time (user: pi, password:
raspberry), issue the following command to start raspi-config and set
the following options.

::

    sudo raspi-config

Then change the following settings

-  ``Change User Password`` (change the password from the default
   'raspberry')
-  ``Localisation Options`` -> ``Change Locale`` (set and select
   en\_US.UTF-8, if US)
-  ``Localisation Options`` -> ``Change Timezone``
-  ``Interfacing Options`` -> ``SSH`` -> ``Enable``
-  ``Advanced Options`` -> ``Expand Filesystem`` (***required***)
-  Reboot (***required***)

Install Mycodo
~~~~~~~~~~~~~~

Mycodo will be installed by executing install.sh. As a part of the
installation, you will be prompted with a few options to determine which
components to install and configure.

.. code:: bash

    curl -L https://raw.githubusercontent.com/kizniche/Mycodo/master/install/install | bash


Make sure the install script finishes without errors. A log of the
output will be created at ``~/Mycodo/install/setup.log``.

If the install is successful, the web user interface should be
accessible by navigating a web browser to ``https://0.0.0.0/``,
replacing ``0.0.0.0`` with your Raspberry Pi's IP address. The first
time you visit this page, you will be prompted to create an admin user.
After creating an admin user, you will be redirected to the login page.
Once logged in, make sure the host name and version number at the top
left is green, indicating the daemon is running. Red indicates the
daemon is inactive or unresponsive. Ensure any java-blocking plugins are
disabled for all parts of the web interface to function properly.

Install Notes
~~~~~~~~~~~~~

If you want write access to the mycodo files, add your user to the
mycodo group, changing 'pi' to your user if it differs, then re-log in
for the changes to take effect.

::

    sudo adduser pi mycodo

In certain circumstances after the initial install or an upgrade, the
mycodo daemon will not be able to start because of a missing or corrupt
pip package. I'm still trying to understand why this happens and how to
prevent it. If you cannot start the daemon, try to reinstall the
required python modules with the following command:

::

    sudo ~/Mycodo/env/bin/pip install -r ~/Mycodo/install/requirements.txt --upgrade --force-reinstall --no-deps

Then reboot

::

    sudo shutdown now -r

If you receive an unresolvable error during the install, please `create
an issue <https://github.com/kizniche/Mycodo/issues>`__. If you want to
try to diagnose the issue yourself, see `Diagnosing
Issues <#diagnosing-issues>`__.

A minimal set of anonymous usage statistics are collected to help
improve development. No identifying information is saved from the
information that is collected and it is only used to improve Mycodo. No
other sources will have access to this information. The data collected
is mainly how much specific features are used, and other similar
statistics. The data that's collected can be viewed from the 'View
collected statistics' link in the Settings -> General page or in the
file ``~/Mycodo/databases/statistics.csv``. You may opt out from
transmitting this information in the General settings.

Web Server Security
-------------------

An SSL certificate will be generated (expires in 10 years) and stored at
``~/Mycodo/mycodo/mycodo_flask/ssl_certs/`` during the install process
to allow SSL to be used to securely connect to the web interface. If you
want to use your own SSL certificates, replace them with your own.

If using the auto-generated certificate from the install, be aware that
it will not be verified when visiting the web interface using the
``https://`` address prefix (opposed to ``http://``). You may
continually receive a warning message about the security of your site,
unless you add the certificate to your browser's trusted list.

Upgrade
-------

Mycodo can be easily upgraded from the web interface by selecting
``Upgrade`` from the configuration menu. Alternatively, an upgrade can
be initiated from a terminal with the following command:

::

    sudo /bin/bash ~/Mycodo/mycodo/scripts/upgrade_commands.sh upgrade

Manual
------

The Mycodo Manual may be viewed as
`Markdown <https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.rst>`__,
`PDF <https://github.com/kizniche/Mycodo/raw/master/mycodo-manual.pdf>`__,
`HTML <http://htmlpreview.github.io/?https://github.com/kizniche/Mycodo/blob/master/mycodo-manual.html>`__,
or `Plain
Text <https://raw.githubusercontent.com/kizniche/Mycodo/master/mycodo-manual.txt>`__

Donate
------

I have always made Mycodo free, and I don't intend on changing that to
make a profit. However, if you would like to make a donation, you can
find several options to do so at
`KyleGabriel.com/donate <http://kylegabriel.com/donate>`__

Links
-----

Thanks for using and supporting Mycodo, however it may not be the latest
version or it may have been altered if not obtained through an official
distribution site. You should be able to find the latest version on
github or my web site.

https://github.com/kizniche/Mycodo

http://KyleGabriel.com

License
-------

Mycodo is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your
option) any later version.

Mycodo is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the `GNU General Public
License <http://www.gnu.org/licenses/gpl-3.0.en.html>`__ for more
details.

A full copy of the GNU General Public License can be found at
http://www.gnu.org/licenses/gpl-3.0.en.html

This software includes third party open source software components.
Please see individual files for license information, if applicable.

Languages
---------

-  Native: English
-  Complete: `Español (Spanish) <#espa%C3%B1ol-spanish>`__,
   `Deutsche (German) <#deutsche-german>`__,
   `Français (French) <#fran%C3%A7ais-french>`__,
   `Italian <#italian>`__,
   `Portuguese <#portuguese>`__,
   `Russian <#russian>`__, and
   `Chinese <#chinese>`__

By default, mycodo will display the default language set by your browser. You may also
force a language in the settings at ``[Gear Icon]`` -> ``Configure`` ->
``General`` -> ``Language``

If you would like to improve the translations, you can submit a pull request with an
amended .po file from ~/Mycodo/mycodo/mycodo_flask/translations/ or start a
`New Issue <https://github.com/kizniche/Mycodo/issues/new>`__ detailing the corrections.

English
~~~~~~~

The native language used in the software.

Deutsche (German)
~~~~~~~~~~~~~~~~~

Mycodo ist ein automatisiertes Überwachungs- und Regelsystem, das auf
dem Raspberry Pi (Versionen Zero, 1, 2 und 3) läuft.

Ursprünglich zur Kultivierung von essbaren Pilzen entwickelt, hat Mycodo
die Fähigkeit, viel mehr zu tun, einschließlich der Kultivierung von
Pflanzen, Kultivierung von Mikroorganismen, Aufrechterhaltung der
Imkerei-Homöostase, Inkubation von Tieren und Eiern, Aufrechterhaltung
aquatischer Systeme, Alterung von Käse, Fermentierung von Lebensmitteln
und Tabak, Kochen Essen (sous-vide) und mehr.

Das System umfasst ein Backend (Daemon) und ein Frontend
(Benutzerschnittstelle). Das Backend führt Messungen von Sensoren und
Geräten durch und koordiniert dann verschiedene Reaktionen auf diese
Messungen, einschließlich der Fähigkeit, Ausgänge (Relais, PWM,
drahtlose Ausgänge) zu modulieren, Umgebungsbedingungen mit elektrischen
Geräten unter PID-Kontrolle zu regulieren (stetige Regelung oder
Umschaltung) Zeit), Timer planen, Fotos aufnehmen und Videos streamen,
Aktionen auslösen, wenn Messungen bestimmte Bedingungen erfüllen (Relais
modulieren, Befehle ausführen, per E-Mail benachrichtigen usw.) und
vieles mehr. Das Frontend ist eine Webschnittstelle, die eine einfache
Navigation und Konfiguration von jedem browserfähigen Gerät ermöglicht.

Español (Spanish)
~~~~~~~~~~~~~~~~~

Mycodo es un sistema de control remoto y automatizado con un enfoque en
la modulación de las condiciones ambientales. Fue construido para
ejecutarse en el Raspberry Pi (versiones Zero, 1, 2 y 3) y tiene como
objetivo ser fácil de instalar y operar.

El sistema central coordina un conjunto diverso de respuestas a las
mediciones de sensores, incluyendo acciones tales como grabación de
cámara, notificaciones por correo electrónico, activación /
desactivación de relés, regulación con control PID y más.

Mycodo se ha utilizado para cultivar hongos gourmet, cultivar plantas,
cultivar microorganismos, mantener la homeostasis del apiario de abejas,
incubar huevos de serpiente y animales jóvenes, envejecer quesos,
fermentar alimentos, mantener sistemas acuáticos y mucho más.

Français (French)
~~~~~~~~~~~~~~~~~

Mycodo est un système de surveillance à distance et de régulation
automatisée, axé sur la modulation des conditions environnementales. Il
a été construit pour exécuter dans le Raspberry Pi (versions Zero, 1, 2
et 3) et vise à être facile à installer et à utiliser.

Le système de base coordonne un ensemble divers de réponses aux mesures
de capteurs, y compris des actions telles que l'enregistrement de
caméra, les notifications par courrier électronique, l'activation /
désactivation de relais, la régulation avec contrôle PID, et plus
encore.

Mycodo a été utilisé pour cultiver des champignons gourmands, cultiver
des plantes, cultiver des micro-organismes, entretenir l'homéostasie du
rucher des abeilles, incuber les œufs de serpent et les jeunes animaux,
vieillir les fromages, fermenter les aliments, entretenir les systèmes
aquatiques et plus encore.

Italian
~~~~~~~

Mycodo è un sistema di monitoraggio e regolazione automatico che è
stato creato per funzionare su Raspberry Pi (versioni Zero, 1, 2 e 3).

Originariamente progettato per coltivare funghi commestibili, Mycodo
è cresciuto fino a comprendere la possibilità di fare molto di più,
coltivando piante, coltivando microrganismi, mantenendo l'omeostasi
delle api apistiche del miele, incubando animali e uova, mantenendo
sistemi acquatici, formaggi stagionati, alimenti fermentati e tabacco,
cucinando cibo (sous-vide), e altro ancora.

Il sistema comprende un backend (demone) e un frontend (interfaccia
utente). Il back-end esegue misurazioni da sensori e dispositivi,
quindi coordina una serie diversificata di risposte a tali misurazioni,
inclusa la possibilità di modulare le uscite (relè, PWM, prese wireless),
regola le condizioni ambientali con dispositivi elettrici sotto controllo
PID (regolazione costante o commutazione tempo), programmare i timer,
acquisire foto e riprodurre video in streaming, attivare azioni quando
le misurazioni soddisfano determinate condizioni (moduli relè, comandi
di esecuzione, notifica via e-mail, ecc.) e altro. Il frontend è
un'interfaccia web che consente una facile navigazione e configurazione
da qualsiasi dispositivo abilitato per il browser.

Portuguese
~~~~~~~~~~
Mycodo é um sistema automatizado de monitoramento e regulação que foi
construído para rodar no Raspberry Pi (versões Zero, 1, 2 e 3).

Originalmente projetado para cultivar cogumelos comestíveis, o Mycodo
cresceu para incluir a capacidade de fazer muito mais, incluindo
cultivar plantas, cultivar microorganismos, manter a homeostase do
apiário de abelhas, incubar animais e ovos, manter sistemas aquáticos,
queijos envelhecidos, fermentar alimentos e tabaco, cozinhar comida
(sous-vide) e muito mais.

O sistema compreende um backend (daemon) e um frontend (interface de
usuário). O backend realiza medições a partir de sensores e dispositivos
e coordena um conjunto diversificado de respostas a essas medições,
incluindo a capacidade de modular saídas (relés, PWM, tomadas sem fio),
regular condições ambientais com dispositivos elétricos sob controle PID
(regulação estável ou troca tempo), agendar cronômetros, capturar fotos
e transmitir vídeo, desencadear ações quando as medições atenderem a
determinadas condições (modular relés, executar comandos, notificar por
e-mail etc.) e muito mais. O frontend é uma interface da Web que permite
fácil navegação e configuração a partir de qualquer dispositivo
habilitado para navegador.

Russian
~~~~~~~

Первоначально разработанный для выращивания съедобных грибов, Mycodo
вырос, чтобы включать в себя способность делать гораздо больше, в том
числе выращивать растения, культивировать микроорганизмы, поддерживать
гомеостаз медоносной пчелы, инкубировать животных и яйца, поддерживать
водные системы, стареющие сыры, ферментировать продукты и табак,
готовить еда (sous-vide) и многое другое.

Система содержит бэкэнд (демон) и интерфейс (пользовательский
интерфейс). Бэкэнд выполняет измерения от датчиков и устройств, затем
координирует разнообразные ответы на эти измерения, в том числе
возможность модулировать выходы (реле, ШИМ, беспроводные розетки),
регулировать условия окружающей среды с помощью электрических устройств
под ПИД-регулированием (устойчивое регулирование или изменение время),
расписание таймеров, сбор фотографий и потоковое видео, триггерные
действия, когда измерения соответствуют определенным условиям
(модулировать реле, выполнять команды, уведомлять по электронной почте
и т. д.) и многое другое. Интерфейс - это веб-интерфейс, который
обеспечивает удобную навигацию и настройку с любого устройства с
поддержкой браузера.

Chinese
~~~~~~~

Mycodo最初设计用于种植可食用的蘑菇，已经发展到能够做更多的工作，包括种植植物，
培养微生物，维持蜂蜜蜂房稳态，孵化动物和鸡蛋，维持水生系统，陈年奶酪，
发酵食品和烟草，烹饪食物（sous-vide）等等。

该系统包括后端（守护进程）和前端（用户界面）。后端从传感器和设备进行测量，
然后协调对这些测量的各种响应，包括调制输出（继电器，PWM，无线插座）的能力，
通过PID控制的电气设备调节环境条件（稳定调节或转换时间），安排计时器，捕获照片和流视频，
在测量满足特定条件时触发动作（调制继电器，执行命令，通过电子邮件通知等）
等等。前端是一个Web界面，可以从任何支持浏览器的设备轻松导航和配置。


.. |Build Status| image:: https://travis-ci.org/kizniche/Mycodo.svg?branch=master
   :target: https://travis-ci.org/kizniche/Mycodo
.. |Codacy Badge| image:: https://api.codacy.com/project/badge/Grade/5b9c21d5680f4f7fb87df1cf32f71e80
   :target: https://www.codacy.com/app/Mycodo/Mycodo?utm_source=github.com&utm_medium=referral&utm_content=kizniche/Mycodo&utm_campaign=Badge_Grade
.. |DOI| image:: https://zenodo.org/badge/30382555.svg
   :target: https://zenodo.org/badge/latestdoi/30382555
.. |Mycodo| image:: http://kylegabriel.com/projects/wp-content/uploads/sites/3/2016/05/Mycodo-3.6.0-tango-Graph-2016-05-21-11-15-26.png
   :target: http://kylegabriel.com/projects/
