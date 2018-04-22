# What?
It's a weather station that collects sensor data but also spins up a web sever that lets you look at the time series data from everywhere you want.

Hardware you need
- Raspberry Pi (and, you know, micro SD card and power supply. Maybe even an Ethernet cable.)
- TFA Dostmann "AirCO2ntrol Mini" CO2-Monitor or CO2Meter RAD-0301 Mini CO2 Monitor (they are essentially the same)


# How?
The whole thing works as follows. Someone really smart [reverse
engineered](https://hackaday.io/project/5301-reverse-engineering-a-low-cost-usb-co-monitor/log/17909-all-your-base-are-belong-to-us)
the way the CO2 sensor reports temperature and CO2 levels via USB. We use this
to scrape the data with the Raspberry Pi from the CO2 sensor.

We want to use [Prometheus](https://prometheus.io/) to store time-series data
of all sensor data. So what we need to do is we spin up a web server on the
Raspberry Pi and make the sensor readouts available via HTTP. Prometheus runs
as a daemon on the Raspberry Pi and it is configured to periodically, say every
10s, request the sensor data via HTTP. Prometheus stores the data and makes it
available for further processing or it can even be federated if you feel the
need to install multiple sensors (lots of sensors, lots of data, lots of
Prometheus daemons, lots of aggregation to do).

In order to visualize the time series data, we toss
[Grafana](https://grafana.com/) into the mix which creates another web server
on the Raspberry Pi. Once we request it from another computer, it returns a
metric ton of Javascript that runs completely in your browser and that can
configured to directly read Prometheus time series data. You can click yourself
a nice visualization for your data. 


# Steps to reproduce
## The Raspberry
Setup your Rasberry Pi so that you can reach it via ssh in your LAN and you
should probably give it a static IP address. Let's call the static IP
`10.0.0.2`. In the remainder I'll also assume you went with the standard
Raspbian operating system.

## Prometheus
Now install Prometheus 
```
# apt-get install prometheus
```
and configure it so that it uses the configuration file within this repository
you can either overwrite /etc/prometheus/prometheus.yml with the configuration
prometheus.yml from this repository or you can simply tell systemd to launch
prometheus with the config file in this repo by adding the line
```
ARGS="-config.file \"/path/to/repo/weather/prometheus.yml\" "
```
to the file /etc/default/prometheus, where  /path/to/repo should be replaced by
-- duh -- the path to the repository.

After that, enable and start the prometheus service
```
# systemctl enable prometheus
# systemctl start prometheus
```
and check if everything went well with
```
# systemctl status prometheus
```
or open up your browser and type in `10.0.0.2:9090` (or whatever the IP of your
rasp is). If it returns a website, Prometheus is running properly.



## The Sensor Readout Script
Start the sensor readout using
```
$ ./read_sensor.py /dev/hidraw0
```
where the argument is the sensor device path (it should be the same in your
case...?). If it crashes, you probably just need to install the missing python
packages. Also, this works with python2.7. This script also spins up the web
server that serves the data to Prometheus.

In order to verify that the script runs, you can type `10.0.0.2:9110` into your
browser (or whatever the IP of your rasp is) and it will return your request
with current sensor data. You should be able to find the CO2 level and the
temperature in there.


## Grafana
Now everything that remains is the data visualization and we're going to use
Grafana for that. There doesn't seem to be an official build for the Raspberry
Pi but you can get it [here](https://github.com/fg2it/grafana-on-raspberry)
nonetheless. Pick the the armhf version for the Raspberry Pi.

By default, Grafana is configured to start up a web server listening to port
3000. If the weather service is the sole purpose of the Raspberry Pi, you can
change it to the default http port 80 by editing the `http_port` line in the
server section of the grafana configuration located at
`/etc/grafana/grafana.ini`. Note that for ports below 1024, you need special
permissions. To give these to grafana-server, type
```
# setcap 'cap_net_bind_service=+ep' /usr/sbin/grafana-server
```
You can also configure https which is a fairly good idea if you want to access
the weather station from outside your LAN. Then enable and start the
grafana-server service
```
# systemctl enable grafana-server.service
# systemctl start grafana-server.service
```

Now you can open up your browser and type in the IP address of your Raspberry,
say, `10.0.0.2` and the Grafana web server will deliver the visualization
interface directly to your browser. Log in as `admin` with the password `admin`
and proceed to change the password.

Grafana supports Prometheus data sources out of the box, so all you have to do
is to point Grafana to the Prometheus time series data. In the Grafan user
interface go to `Preferences -> Data Sources` and configure a data source as
- type: Prometheus
- URL: `http://10.0.0.2:9090`
- Access: direct

Then click `Save & Test`. Note that you can't enter the URL
`http://localhost:9090` even though Grafana runs on the Raspberry Pi itself.
This is because the Grafana Server doesn't actually fetch the data from
Prometheus itself. It only delivers a blob of JavaScript to your browser which
not generates all the visualizations but also fetches the data to visualize.
That means that the URL you type in as a data source must be the URL from which
your computer can reach the Prometheus data source. From the perspective of
your computer, `localhost` is just itself and not the Raspberry Pi.

With the data source configured, you can now go ahead and configure yourself a
nice Dashboard with the collected metrics. Here's what I did:
![dashboard](/dashboard.png)

Finally, if you want others to have access, don't give them your admin
credentials but simply create new users in the Grafana interface so that they
create their own interfaces (or view your predefined ones).

