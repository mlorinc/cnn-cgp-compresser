#!/bin/bash
set -e
export TIMESTAMP=$(date '+%d_%m_%Y_%H_%M_%S')
for file in *; do
        pushd . > /dev/null
        cd $file 
        if [ -f jobs_info.txt ] ; then
            ~/scripts/job_backup.sh "$1" "$2" "$3"
        fi        
        popd > /dev/null
done
unset TIMESTAMP
