#!/bin/bash
ARGS=()
for arg in "$@"; do
    if [[ "$arg" == *"azmq="* ]]; then
        CLEANED=$(echo "$arg" | sed -E 's/,?azmq=b=tcp\\[^,]+//g' | sed -E 's/azmq=b=tcp\\[^,]+,?//g')
        ARGS+=("$CLEANED")
    else
        ARGS+=("$arg")
    fi
done
exec ffmpeg "${ARGS[@]}"
