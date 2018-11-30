
VNFNAME=$1
VNFDNAME=$1"VNFD"
VNFDFILE=$1"-vnfd.yaml"
echo 3:$3 4:$4 5:$5 6:$6
if [ "${2}" == "ssh" ] ; then
	sudo cp ubuntu1604-vnfd.yaml $VNFDFILE
        #sudo cp para-ubuntu-vnfd.yaml $VNFDFILE
        #sudo ./config_generate.sh ubuntu1604 '1024 MB' '5 GB' 1
elif [ "${2}" == "nmap" ] ; then
	#sudo cp custom-vnfd.yaml $VNFDFILE
        sudo cp para-ubuntu-vnfd.yaml $VNFDFILE
        sudo ./config_generate.sh ubuntu1604 '2048 MB' '5 GB' 1
elif [ "${2}" == "proxy" ] ; then
	#sudo cp proxy-vnfd.yaml $VNFDFILE
        sudo cp para-ubuntu-vnfd.yaml $VNFDFILE
        sudo ./config_generate.sh ubuntu1604python '2048 MB' '5 GB' 1
elif [ "${2}" == "epc" ] ; then
	#sudo cp epc-vnfd.yaml $VNFDFILE
        sudo cp para-ubuntu-vnfd.yaml $VNFDFILE
        sudo ./config_generate.sh ubuntu '2048 MB' '10 GB' 1
elif [ "${2}" == "nextepc" ] ; then
        #sudo cp para-ubuntu-vnfd.yaml $VNFDFILE
        sed '/        user_data: |/r install_basic.txt' para-ubuntu-vnfd.yaml|sudo tee $VNFDFILE
        sudo ./config_generate.sh next-epc '2048 MB' '5 GB' 1
elif [ "${2}" == "config" ] ; then
        sed '/        user_data: |/r install_basic.txt' para-ubuntu-vnfd.yaml|sudo tee $VNFDFILE
        sudo ./config_generate.sh "${3}" "${4}" "${5}" "${6}"
elif [ "${2}" == "config3" ] ; then
        sed '/        user_data: |/r install_basic.txt' para-ubuntu-vnfd3.yaml|sudo tee $VNFDFILE
        sudo ./config_generate.sh "${3}" "${4}" "${5}" "${6}"

else
	sudo cp ubuntu1604-vnfd.yaml $VNFDFILE
fi


echo $VNFNAME" "$VNFDNAME" "$VNFDFILE
tacker vnfd-create --vnfd-file $VNFDFILE $VNFDNAME
sleep 1
tacker vnf-create --vnfd-name $VNFDNAME --vim-name Site --param-file config.yaml $VNFNAME
SERVERSTATUS=`openstack server list|grep $VNFNAME| awk '{print $6}'`
until [ "${VNFSTATUS}" == "ACTIVE"  ]
do
	sleep 5
	echo "wait for create"
	VNFSTATUS=`tacker vnf-list|grep $VNFNAME|awk '{print $9}'`
	if [ "${VNFSTATUS}" == "ERROR" ] ; then
		break;
	fi
done
echo "VNFNAME is "$VNFNAME" "$1
#VNFNAME=test9
VNFIP=`tacker vnf-list|grep $VNFNAME|awk '{print $7}'|sed 's/}//g'|sed 's/"//g'`
SERVERID=`openstack server list|grep $VNFIP| awk '{print $2}'`
echo "create OK"
echo "server id is "$SERVERID

VNFMNGIP=`openstack server list|grep $VNFIP| awk '{print $10}'|sed 's/net_mgmt=//g'`
echo "vnf access ip is "$VNFMNGIP
openstack console url show $SERVERID


#
#SERVERSTATUS=`openstack server list|grep ubuntu1604| awk '{print $6}'`





#openstack server list
#openstack console url show $SERVERID
#if [ "${SERVERSTATUS}" == "ACTIVE" ] ; then
#	echo "create VNF done...."
#	exit 1
#fi
