#!/bin/sh

printf "Starting factory scripts"
printf "\n"
printf "Starting serialization script"
printf "\n"
python serialization.py

printf "Wait until activation"

python clean_up.py

printf "Factory scripts completed"
printf "\n"
printf "wait until blue LED flash to turn off"
printf "\n"
