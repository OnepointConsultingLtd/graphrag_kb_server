#!/bin/sh
set -e

cd /opt/graphrag_kb_server
exec python3 -m graphrag_kb_server.service.reports.daily_usage_job
