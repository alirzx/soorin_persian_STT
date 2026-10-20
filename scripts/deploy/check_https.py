#!/usr/bin/env python3
"""Fail-closed HTTPS deployment checks without displaying secrets."""
from pathlib import Path
import ipaddress
import re
import sys

path=Path(__file__).resolve().parents[2]/'.env'
if not path.is_file():
    sys.exit('HTTPS preflight failed: .env missing')

values={}
for line in path.read_text(encoding='utf-8').splitlines():
    if '=' not in line or line.lstrip().startswith('#'):
        continue
    key,val=line.split('=',1)
    values[key.strip()]=val.strip().strip("'").strip('"')

def fail(reason):
    sys.exit('HTTPS preflight failed: '+reason)

ip=values.get('STT_HTTPS_HOST','')
bind=values.get('STT_HTTPS_BIND_HOST','')
if not ip or not bind or ip!=bind:
    fail('STT_HTTPS_HOST must equal STT_HTTPS_BIND_HOST (the server LAN IP)')
if ip in {'0.0.0.0','::','127.0.0.1'}:
    fail('Use the actual LAN IP for shared access, not loopback/wildcard')
try:
    ipaddress.ip_address(ip)
except ValueError:
    fail('Use an IP address for this internal-CA deployment profile')
if values.get('UI_BIND_HOST','127.0.0.1') not in {'127.0.0.1','localhost'}:
    fail('UI_BIND_HOST must be loopback, or users can bypass HTTPS authentication')
if values.get('STT_BIND_HOST','127.0.0.1') not in {'127.0.0.1','localhost'}:
    fail('STT_BIND_HOST must be loopback')
if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',values.get('STT_HTTPS_USER','')):
    fail('STT_HTTPS_USER must be a simple nonempty username')
if not re.fullmatch(r'\$2[aby]\$\d\d\$[./A-Za-z0-9]{53}',values.get('STT_HTTPS_PASSWORD_HASH','')):
    fail('STT_HTTPS_PASSWORD_HASH must contain a bcrypt hash, single-quoted in .env')
if values.get('APP_ENV')=='production' and not values.get('APP_API_KEY'):
    fail('APP_API_KEY is required in production (plus browser-aware auth forwarding)')
print('HTTPS preflight passed. Remember to trust the CA on client devices.')
