#!/bin/bash
set -e

sudo systemctl restart piAgent.service
echo ""
systemctl status piAgent.service --no-pager || true
