#!/bin/bash

file=$1
header="# This file is part of the faebryk project\n# SPDX-License-Identifier: MIT"

found_head="$(head -n2 $file)"
hash_1=$(echo -e "$found_head" | md5sum)
hash_2=$(echo -e "$header" | md5sum)

if [ "$hash_1" == "$hash_2" ]; then
    echo "Already found"
    exit 0
fi
echo -e "$file: Found:|$found_head|"
exit 0
#TODO remove exit


awk 'BEGIN{print ""}1' \
    $file | sponge $file