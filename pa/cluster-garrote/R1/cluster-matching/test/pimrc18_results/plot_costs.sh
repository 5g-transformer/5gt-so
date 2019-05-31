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
PLOT_DATA_FILE='num_clusters_and_costs.txt'

ga_lat="245.08151682"
ga_cost="102.398442653"

echo -e "num_clusters\tcost\tga-cost\tga-lat\texec_time" > $PLOT_DATA_FILE

for mapping_file in `ls -v ./cluster_matching*`; do
    cost=`grep "mapping_cost" $mapping_file | grep -o "[0-9]\+.[0-9]\+"`
    exec_time=`grep "execution_time" $mapping_file | grep -o "[0-9]\+.[0-9]\+"`
    num_clusters=`echo $mapping_file | grep -o "[0-9]\+"`
    if [[ -z $cost ]]; then
        cost=-1
    fi
    echo -e "$num_clusters\t$cost\t$ga_cost\t$ga_lat\t$exec_time" >> $PLOT_DATA_FILE
done

gnuplot plotter.gpi

