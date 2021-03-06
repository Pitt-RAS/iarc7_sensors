# iarc7\_sensors

This repository is part of the Pitt RAS effort for IARC Mission 7.  For an overview of the IARC competition as well as the team's efforts and technical approaches, check out our [team website](http://pittras.org/projects/IARC/), and in particular the [technical postmortem post for the project](http://pittras.org/projects/iarc/2018/08/10/update-iarc-technical-postmortem.html).

For other IARC teams finding this repository, we've made it public intentionally. We would love for you to take a look around and send us any questions you have (or any bugfixes you develop). This code is open source and free to use under the GPL, but we do ask that other IARC teams using this code or ideas taken from it cite the Pitt Robotics and Automation Society and do not present the work or the ideas contained within it as their own.

Note: The altimeter node depends on the `libi2c-dev` package, which can be installed by running

    sudo apt-get install libi2c-dev

By default, users don't have permission to access the linux i2c driver.  You can change that by running

    sudo usermod -a -G i2c <user>

If you don't do this, you'll have to run the altimeter node as root.
