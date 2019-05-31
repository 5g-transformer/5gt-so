#!/bin/bash - 
#===============================================================================
#
#          FILE: plot_costs.sh
# 
#         USAGE: ./plot_costs.sh 
# 
#   DESCRIPTION: 
# 
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: YOUR NAME (), 
#  ORGANIZATION: 
#       CREATED: 16/05/18 16:41
#      REVISION:  ---
#===============================================================================

set -o nounset                              # Treat unset variables as an error
PLOT_DATA_FILE='num_clusters_and_latency.txt'

ga_cost="0.0217189698074"
ga_latency="0.0139435399581"

echo -e "num_clusters\tlatency\tga_cost\tga_latency\texec_time" > $PLOT_DATA_FILE

for mapping_file in `ls -v ./cluster_matching*`; do
    cost=`grep "avg_services_delay" $mapping_file | grep -o "[0-9]\+.[0-9]\+"`
    exec_time=`grep "execution_time" $mapping_file | grep -o "[0-9]\+.[0-9]\+"`
    num_clusters=`echo $mapping_file | grep -o "[0-9]\+"`
    if [[ -z $cost ]]; then
        cost=-1
    fi

    echo -e "$num_clusters\t$cost\t$ga_cost\t$ga_latency\t$exec_time" >> $PLOT_DATA_FILE
done

#gnuplot plotter_latency.gpi
gnuplot plotter_latency_ok.gpi

