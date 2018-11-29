# python-osmclient
A python client for osm orchestration

A test commit

# Installation

## python-osmclient
### Install dependencies
```bash
sudo apt-get install python-dev libcurl4-gnutls-dev python-pip libgnutls-dev python-prettytable  
sudo pip install pycurl
```

### Install python-osmclient
    sudo pip install git+https://github.com/mfmarche/python-osmclient


## Snap
```bash
apt install snapd
snap install osmclient --channel=beta
```

# Setup
Set the OSM_HOSTNAME variable to the host of the osm server.

Example
```bash
localhost$ export OSM_HOSTNAME=<hostname>:8008
```

# Examples

## upload vnfd
```bash
localhost$ osm upload-package ubuntu_xenial_vnf.tar.gz
{'transaction_id': 'ec12af77-1b91-4c84-b233-60f2c2c16d14'}
localhost$ osm vnfd-list
+--------------------+--------------------+
| vnfd name          | id                 |
+--------------------+--------------------+
| ubuntu_xenial_vnfd | ubuntu_xenial_vnfd |
+--------------------+--------------------+
```

## upload nsd
```bash
localhost$ osm upload-package ubuntu_xenial_ns.tar.gz
{'transaction_id': 'b560c9cb-43e1-49ef-a2da-af7aab24ce9d'}
localhost$ osm nsd-list
+-------------------+-------------------+
| nsd name          | id                |
+-------------------+-------------------+
| ubuntu_xenial_nsd | ubuntu_xenial_nsd |
+-------------------+-------------------+
```
## vim-list

```bash
localhost$ osm vim-list
+-------------+-----------------+--------------------------------------+
| ro-account  | datacenter name | uuid                                 |
+-------------+-----------------+--------------------------------------+
| osmopenmano | openstack-site  | 2ea04690-0e4a-11e7-89bc-00163e59ff0c |
+-------------+-----------------+--------------------------------------+
```


## instantiate ns
```bash
localhost$ osm ns-create ubuntu_xenial_nsd testns openstack-site
{'success': ''}
localhost$ osm ns-list
+------------------+--------------------------------------+-------------------+--------------------+---------------+
| ns instance name | id                                   | catalog name      | operational status | config status |
+------------------+--------------------------------------+-------------------+--------------------+---------------+
| testns           | 6b0d2906-13d4-11e7-aa01-b8ac6f7d0c77 | ubuntu_xenial_nsd | running            | configured    |
+------------------+--------------------------------------+-------------------+--------------------+---------------+
```

# Bash Completion
python-osmclient uses [click](http://click.pocoo.org/5/).  You can setup bash completion by putting this in your .bashrc:

    eval "$(_OSM_COMPLETE=source osm)"
