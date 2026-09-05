#!/usr/bin/env bash
set -euo pipefail

patterns='rzp_live_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
if rg -n --hidden -g '!node_modules/**' -g '!.git/**' -g '!package-lock.json' -e "$patterns" .; then
  echo "Potential live secret detected" >&2
  exit 1
fi
yaml_credentials='(?i)^\s*([a-z0-9_]*password|[a-z0-9_]*secret|[a-z0-9_]*token):\s+(?!\$\{)[^\s#]+'
if rg --pcre2 -n --hidden -g '*.yml' -g '*.yaml' -g '!.git/**' -e "$yaml_credentials" .; then
  echo "Hardcoded YAML credential detected" >&2
  exit 1
fi
echo "No high-confidence live secret patterns detected"
