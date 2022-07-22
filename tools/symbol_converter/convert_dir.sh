#!/bin/bash

dir=$1
out=$2
mkdir -p $out

run() {
    i=$1
    name=$(basename $i .kicad_sym)
    echo $name
    python3 $(dirname $0)/main.py $i > $out/$name.py || exit 1
    python3 -m black $out/$name.py
} 

for i in $dir/*.kicad_sym; do
    run $i &
done

wait