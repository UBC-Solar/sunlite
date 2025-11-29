### Solar's RPI based Cellular System

#### Set-up

Follow the steps below to fully install, configure, and run Sunlite's RPI-based Cellular System.

1. #### System Requirements

    Hardware

    - Raspberry Pi 4 B
    - SD Card with Raspberry Pi OS
    - USB-CAN adapter (e.g. PCAN)
    - LTE/5G Hotspot (e.g. NETGEAR)
    - Internet connection (Ethernet)

    Software

    - Raspberry Pi OS (Bookworm)
    - Python 3.10+
    - InfluxDB 2.x Instance (Local or ELEC Computer)
    - Tailscale

2. #### Clone Repository on RPI

    ```bash
    git clone https://github.com/UBC-Solar/sunlite.git 
    cd sunlite
    ```

3. #### Copy Environment Variables

    Copy over the example environment and edit it to include your desired endpoints

    ```bash
    cp .env.example .env
    nano .env
    ```

    ```bash
    INFLUX_URL="http://<influx-ip>:8086"
    INFLUX_ORG="UBC Solar"
    INFLUX_BUCKET="<replace_with_real_bucket>"
    INFLUX_TOKEN="<replace_with_real_token>"
    ```

4. #### Run Installation Scripts

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

5. #### Ensure Tailscale is Running

    First enable tailscale by running this command and setting tailscale up.

    ```bash
    sudo tailscale up
    ```

    Then, check Tailscale status to the RPI, after checking the status, a list of networks on the current Tailscale network will be revealed, check this RPI's Tailscale IP and ensure it is on the network and fully connected.

    ```bash
    tailscale status
    tailscale ip
    ```

6. #### Running the Script Manually or with Service (Optional)

    On the current variation of sunlite, you can run the script either manually or as a service. Manually running the script requires the user to *ssh* into the RPI each time, while as a service, the script runs on startup whenever the RPI has a solid network connection.

    To manually run the script the user must enter the virtual environment and directly run it from there.

    ```bash
    source .venv/bin/activate

    cd src/influx_cellular
    python3 cell_script.py
    ```

    To run the script as a service, the user must use the systemd service file provided in <installations/cellular-logger.service>. This is activated when the user ran *install.sh*. 

    The service only activates when all 3 requirements are up, otherwise it won't run:
    - network-online.target (interfaces fully up)
    - tailscaled.service (if installed)
    - influxdb.service

    STOP/DISABLE SERVICE:

    To stop this service temporarily until the next reboot, run the following command:

    ```bash
    sudo systemctl stop cellular-logger
    ```

    To disable this service and follows through even with reboots, run:

    ```bash
    sudo systemctl stop cellular-logger
    sudo systemctl disable cellular-logger
    ```

    START/AUTORUN SERVICE:

    To restart this service manually but not at the next reboot, use this following command:

    ```bash
    sudo systemctl start cellular-logger
    ```

    To enable autorun starting every reboot, utilize this command:

    ```bash
    sudo systemctl enable cellular-logger
    ```

    DEBUGGING:

    To check the status of the service, use this command:

    ```bash
    sudo systemctl status cellular-logger
    ```

    To view all the logs, use this command:

    ```bash
    journalctl -u cellular-logger -f
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