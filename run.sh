#!/bin/bash

logs=$(find ../data/k8s/ci-ingress-gce-e2e/1370250008544153600 -name "*.log")

for t in $(ls ingress*)
do
    for log in $logs
    do
        grep $t $log > $log.$t
        [[ ! -s $log.$t ]] && rm $log.$t
    done
done