### Solar's RPI based Cellular System

#### Set-up

Follow the steps below to fully install, configure, and run Sunlite's RPI-based Cellular System.

1. #### System Requirements

    Hardware

    - Raspberry Pi 4 B
    - Micro SD Card with Raspberry Pi OS
    - USB-CAN adapter (e.g. PCAN)
    - LTE/5G Hotspot (e.g. NETGEAR)
    - Internet connection (Ethernet)

    Software

    - Raspberry Pi OS (Bookworm)
    - Python 3.10+
    - InfluxDB 2.x Instance (Local or ELEC Computer)
    - Tailscale

2. #### Raspbery Pi Imager

    If the Micro SD card is not installed with the RPI OS (Bookworm), ensure to install it using the [RPI Imager](https://www.raspberrypi.com/software/). After installation, there are four categories that must be chosen.

    1. Device
        - Choose the Raspberry Model available (likely 4B or 5)
    2. OS
        - Choose the Raspberry Pi OS (64-bit)
    3. Storage
        - Choose the micro SD card as storage
    4. Customization
        - Hostname
            - Choose sunlite as the hostname
        - Localization
            - Choose the country/city, pick Canada
        - User
            - Set sunlite as the user again
            - Set a standard password
        - Wi-Fi
            - Enter in the hostname and password of the network being used
            - Check this on the hotspot being used, with NETGEAR it is on the front page
        - Remote Access
            - Ensure to enable to *ssh*, this is a MUST have
            - Pick the password option
        - Raspberry Pi Connect
            - Nice to have but not necessary to setup

    After this, install and write the data to the micro SD card, now it's ready to be used.

3. #### SSH to the RPI

    There are two possible ways to setting up the RPI, one on a monitor and the second using a remote computer.

    1. In order to *ssh* into the RPI, the accessing computer must SHARE the same network being used as the RPI. Then, find the RPI's IP address, this is usually within the connectivity/Wi-Fi location on the hotspot, find the IP address. With this use the following command to *ssh* into the RPI:

        ```bash
        ssh sunlite@<ip-address>
        ```

    2. Connect a monitor to the Raspberry Pi using a micro-HDMI cable, and ensure a keyboard is also connected. This allows you to skip the *ssh* step and edit directly to the RPI on the monitor. Follow the following steps until Tailscale is installed, and then *ssh* with Tailscale from a remote computer.

4. #### Clone Repository on RPI

    To clone the main (production) repository of Sunlite use this command:

    ```bash
    git clone https://github.com/UBC-Solar/sunlite.git 
    cd sunlite
    ```

    When doing testing on a RPI, branches can be cloned as well:

    ```bash
    git clone --branch <branch-name> https://github.com/UBC-Solar/sunlite.git 
    cd sunlite
    ```

    To git pull into the RPI, ensure all changes made by the RPI has been committed or stashed.

    ```bash
    git pull origin <branch-name>
    ```

    Failure to properly commit or stash results in this error statement being printed, and changes are unabled to be pulled.

    ```bash
    sunlite@sunlite:~/sunlite $ git pull origin user/tonychen-2006/tailscale_rpi
    remote: Enumerating objects: 7, done.
    remote: Counting objects: 100% (7/7), done.
    remote: Compressing objects: 100% (1/1), done.
    remote: Total 4 (delta 3), reused 4 (delta 3), pack-reused 0 (from 0)
    Unpacking objects: 100% (4/4), 357 bytes | 119.00 KiB/s, done.
    From https://github.com/UBC-Solar/sunlite
    * branch            user/tonychen-2006/tailscale_rpi -> FETCH_HEAD
    37f068c..d50caaa  user/tonychen-2006/tailscale_rpi -> origin/user/tonychen-2006/tailscale_rpi
    Updating 37f068c..d50caaa
    error: Your local changes to the following files would be overwritten by merge:
            installations/setup_python.sh
    Please commit your changes or stash them before you merge.
    Aborting
    ```

5. #### Run Installation Scripts

    Everything needed for the Pi (Python venv, dependencies, permissions, systemd files) is automated. 

    This automatically:
    - Installs Python & system packages
    - Creates a virtual environment
    - Installs all Python dependencies
    - Sets up InfluxDB CLI
    - Configures Tailscale
    - Prepares the cellular logging services

    ```bash
    cd installations
    sudo bash install.sh
    ```

6. #### Ensure Tailscale is Running

    First enable tailscale by running this command and setting tailscale up.

    ```bash
    sudo tailscale up
    ```

    After running this command, Tailscale will ask to authenticate, copy and go to the link, login with UBC Solar's admin github account. You should see the following command in the RPI's terminal if done correctly:

    ```bash
    To authenticate:

            https://login.tailscale.com/a/bf5b250015f57
    ```

    Then, check Tailscale status to the RPI, after checking the status, a list of networks on the current Tailscale network will be revealed, check this RPI's Tailscale IP and ensure it is on the network and fully connected. The IP is a string of numbers like 100.117.111.10 for example.

    ```bash
    tailscale status
    tailscale ip
    ```

    After enabling Tailscale, this allows users to access the RPI with Tailscale instead of using other methods of *ssh*. Below is an example of using Tailscale to access the RPI.

    ```bash
    ssh sunlite@<tailscale-ip-address>
    ```

7. #### Debugging and Testing

    Inside of the tools/ folder, there are multiple files to help test Sunlite's functionailty. The <can_messages.yaml> file MUST be updated whenever the DBC is updated for testing to be accurate.

    - simulate_can.py     : Generates test CAN frames of Solar's full CAN BUS without the necessary hardware
    - can_messages.yaml   : Template for CAN traffic, contains all of Solar's CAN messages
    - characterization.py : Measures the total number of influx fields recieved from a CSV

    To run a simulation, run this command:

    ```bash
    cd tools
    python3 simulate_can.py
    ```

    To evaluate the total fields recieved by influxDB:

    ```bash
    cd tools
    python3 characterization.py
    ```