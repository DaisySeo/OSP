#!/bin/bash

declare -a words

while true
do

  read -p "Enter a new word: " word

  case $word in
    quit)  exit 1 ;;
    list)  echo ${words[*]} ;;
    *)   words+=($word)
         echo Length : ${#words[@]} ;;
  esac

done
