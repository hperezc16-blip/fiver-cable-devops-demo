#!/usr/bin/env sh
set -eu

for port in 8081 8082 8083 8084; do
  echo "Validando http://localhost:${port}/health"
  curl --fail --silent "http://localhost:${port}/health"
  echo
done

