#!/bin/sh
rm -rf pool
rm -rf dists
mkdir -p pool/osmclient
mv deb_dist/*.deb pool/osmclient/
mkdir -p dists/unstable/osmclient/binary-amd64/
apt-ftparchive packages pool/osmclient > dists/unstable/osmclient/binary-amd64/Packages
gzip -9fk dists/unstable/osmclient/binary-amd64/Packages
echo 'dists/**,pool/osmclient/*.deb'
