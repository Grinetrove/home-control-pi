#!/bin/bash
set -e

journalctl -u piAgent.service -f
