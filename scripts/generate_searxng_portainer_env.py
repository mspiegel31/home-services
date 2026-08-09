#!/usr/bin/env python3
"""Generate the Portainer environment values for the SearXNG stack."""

import argparse
import secrets
import subprocess
import sys


parser = argparse.ArgumentParser()
parser.add_argument("--hostname", default="searxng.electricgarage.net")
parser.add_argument("--api-hostname", default="searxng-api.electricgarage.net")
parser.add_argument("--username", default="omp-agent")
args = parser.parse_args()

agent_password = secrets.token_urlsafe(32)
try:
    bcrypt_hash = subprocess.run(
        ["htpasswd", "-bnBC", "14", args.username, agent_password],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip().split(":", 1)[1]
except FileNotFoundError:
    sys.exit("htpasswd is required (included with macOS).")
except (IndexError, subprocess.CalledProcessError) as error:
    detail = getattr(error, "stderr", "")
    sys.exit(detail.strip() or "htpasswd could not generate a bcrypt hash.")

# The Caddyfile uses {$$SEARXNG_BASICAUTH} so Compose passes the literal
# {$SEARXNG_BASICAUTH} to Caddy, which does its own env var substitution.
# Portainer should receive the raw bcrypt hash with unescaped $ characters.
basicauth_line = f"SEARXNG_BASICAUTH={args.username} {bcrypt_hash}"

print("Paste these entries into Portainer's stack environment-variable UI:\n")
print(f"SEARXNG_HOSTNAME={args.hostname}")
print(f"SEARXNG_API_HOSTNAME={args.api_hostname}")
print(f"SEARXNG_SECRET={secrets.token_hex(32)}")
print(basicauth_line)
print(f"\nTest locally before deploying:")
print(f"  http -j --auth '{args.username}:{agent_password}' \\")
print(f"    'https://{args.api_hostname}/search?q=osint&format=json' \\")
print(f"    Accept:application/json")
print(f"\nStore this separately in your password manager. Oh-my-pi needs it later:")
print(f"SEARXNG_BASIC_PASSWORD={agent_password}")
