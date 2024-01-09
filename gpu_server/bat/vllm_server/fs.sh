#!/bin/bash

mnt_result=$(mount | grep /mnt)

if [[ $mnt_result == *"rw,"* ]]; then
    echo "The mount result of /dev/nvme0n1p4 is read-write"
elif [[ $mnt_result == *"ro,"* ]]; then
    echo "The mount result of /dev/nvme0n1p4 is read-only"
else
    echo "The mount result of /dev/nvme0n1p4 is unknown"
fi
