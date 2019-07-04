#!/bin/bash

# wait-for.sh -t 30 -l url[ status][ -l url[ status]]... command ...
set -e

waitfor() {
  local host=$1
  local port=200
  [[ -n $2 ]] && port=$2
  echo -n "waiting $host "
  until [ $(curl -s -o /dev/null -w "%{http_code}" $host) -eq $port ]; do
    echo -n "."
    sleep 1
  done
  echo "...ok"
}

while [[ "$1" = "-l" ]]; do
  shift
  _args=$1
  shift
  if [[ $1 =~ ^[0-9]+$ ]]; then
    _args=$_args\ $1
    shift
  fi
  waitfor $_args
done

cmd="$@"

echo "starting service"
exec "$@"