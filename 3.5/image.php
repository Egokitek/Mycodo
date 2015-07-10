<?php
/*
*  image.php - displays images when image directory is protected by the
*              web server
*
*  Copyright (C) 2015  Kyle T. Gabriel
*
*  This file is part of Mycodo
*
*  Mycodo is free software: you can redistribute it and/or modify
*  it under the terms of the GNU General Public License as published by
*  the Free Software Foundation, either version 3 of the License, or
*  (at your option) any later version.
*
*  Mycodo is distributed in the hope that it will be useful,
*  but WITHOUT ANY WARRANTY; without even the implied warranty of
*  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
*  GNU General Public License for more details.
*
*  You should have received a copy of the GNU General Public License
*  along with Mycodo. If not, see <http://www.gnu.org/licenses/>.
*
*  Contact at kylegabriel.com
*/

####### Configure #######
$install_path = "/var/www/mycodo";


$image_dir = $install_path . "/images/";
$still_dir = $install_path . "/camera-stills/";
$hdr_dir = $install_path . "/camera-hdr/";
$mycodo_client = $install_path . "/cgi-bin/mycodo-client.py";

header('Content-Type: image/jpeg');

if ($_GET['graphtype'] == 'separate' || $_GET['graphtype'] == 'combined' || $_GET['graphtype'] == 'default') {
    readfile($image_dir . 'graph-' . $_GET['sensortype'] . $_GET['graphtype'] . $_GET['graphspan'] . '-' . $_GET['id'] . '-' . $_GET['sensornumber'] . '.png');
} elseif ($_GET['graphtype'] == 'custom-combined') {
    readfile($image_dir . 'graph-' . $_GET['graphtype'] . '-' . $_GET['id'] . '.png');
} elseif ($_GET['graphtype'] == 'custom-separate') {
    readfile($image_dir . 'graph-' . $_GET['graphtype'] . '-' . $_GET['id'] .  '-' . $_GET['sensornumber'] . '.png');
} elseif ($_GET['graphtype'] == 'legend-small') {
    $id = uniqid();
    shell_exec($mycodo_client . ' --graph mone legend-small none' . $id . ' 0');
    readfile($image_dir . 'graph-' . $_GET['graphtype'] . '-' . $id . '.png');
} elseif ($_GET['graphtype'] == 'legend-full') {
    $id = uniqid();
    shell_exec($mycodo_client . ' --graph none legend-full none' . $id . ' 0');
    readfile($image_dir . 'graph-' . $_GET['graphtype'] . '-' . $id . '.png');
} else {
    switch ($_GET['span']) {
    case 'cam-still':
        $files = scandir($still_dir, SCANDIR_SORT_DESCENDING);
        $newest_file = $files[0];
        readfile($still_dir . $newest_file);
        break;
    case 'cam-hdr':
        $files = scandir($still_dir, SCANDIR_SORT_DESCENDING);
        $newest_file = $files[0];
        readfile($still_dir . $newest_file);
        break;
    }
}
?>
