#!/bin/bash
# Convenience script - redirects to the actual script location
"$(dirname "$0")/scripts/test/run-all-tests.sh" "$@"
