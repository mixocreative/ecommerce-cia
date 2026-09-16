#!/bin/sh
# Installs the versioned pre-push gate into this clone.
cp "$(dirname "$0")/pre-push" "$(dirname "$0")/../.git/hooks/pre-push" && chmod +x "$(dirname "$0")/../.git/hooks/pre-push" && echo installed
