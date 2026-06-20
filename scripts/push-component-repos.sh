#!/usr/bin/env bash
# Push monorepo subdirectories to standalone GitHub repos under AetherAIorg.
set -euo pipefail

ORG="AetherAIorg"
SRC="${1:-/Users/karman/Desktop/projects/aether_org}"
WORK="${TMPDIR:-/tmp}/aether-push-$$"
mkdir -p "$WORK"

push_dir() {
  local name="$1"
  local subpath="$2"
  local dest="$WORK/$name"

  echo ""
  echo "=== $ORG/$name ($subpath) ==="
  rm -rf "$dest"
  mkdir -p "$dest"
  rsync -a --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.pytest_cache' \
    "$SRC/$subpath/" "$dest/"

  cd "$dest"
  if [[ ! -f .gitignore ]]; then
    cat > .gitignore <<'EOF'
.env
node_modules/
.next/
.venv/
__pycache__/
.pytest_cache/
.DS_Store
*.db
EOF
  fi

  git init -b main >/dev/null
  git add -A
  if git diff --cached --quiet; then
    echo "skip $name (empty)"
    return 0
  fi
  git commit -m "Sync from aether_org monorepo ($(date +%Y-%m-%d))" >/dev/null

  local url="https://github.com/$ORG/$name.git"
  git remote add origin "$url" 2>/dev/null || git remote set-url origin "$url"
  if git push -u origin main --force; then
    echo "ok $url"
  else
    echo "FAIL $url — create empty repo at https://github.com/orgs/$ORG/repositories/new?name=$name"
    return 1
  fi
}

push_pages_external() {
  local name="margin_github_pages"
  local dest="$WORK/pages-karman"
  echo ""
  echo "=== karman103/margin_github_pages ==="
  rm -rf "$dest"
  rsync -a --delete \
    --exclude '.git' \
    "$SRC/margin_github_pages/" "$dest/"
  cd "$dest"
  git init -b main >/dev/null
  git add -A
  git commit -m "Sync from aether_org monorepo ($(date +%Y-%m-%d))" >/dev/null
  git remote add origin "https://github.com/karman103/margin_github_pages.git" 2>/dev/null || \
    git remote set-url origin "https://github.com/karman103/margin_github_pages.git"
  git push -u origin main --force && echo "ok karman103/margin_github_pages"
}

failures=0
push_dir "metricgraph" "metricgraph" || failures=$((failures + 1))
push_dir "integration_hub" "integration_hub" || failures=$((failures + 1))
push_dir "ingest_engine" "ingest_engine" || failures=$((failures + 1))
push_dir "registry_governance" "registry_governance" || failures=$((failures + 1))
push_dir "margin_sdk" "margin_sdk" || failures=$((failures + 1))
push_dir "margin_github_pages" "margin_github_pages" || failures=$((failures + 1))

echo ""
echo "=== AetherAIorg/margin_github_pages.github.io ==="
PAGES_DEST="$WORK/pages-org"
rm -rf "$PAGES_DEST"
rsync -a --delete --exclude '.git' "$SRC/margin_github_pages/" "$PAGES_DEST/"
cd "$PAGES_DEST"
git init -b main >/dev/null
git add -A
git commit -m "Sync from aether_org monorepo ($(date +%Y-%m-%d))" >/dev/null
git remote add origin "https://github.com/AetherAIorg/margin_github_pages.github.io.git" 2>/dev/null || \
  git remote set-url origin "https://github.com/AetherAIorg/margin_github_pages.github.io.git"
if git push -u origin main --force; then
  echo "ok AetherAIorg/margin_github_pages.github.io"
else
  echo "FAIL margin_github_pages.github.io"
  failures=$((failures + 1))
fi

push_pages_external || failures=$((failures + 1))

rm -rf "$WORK"
exit "$failures"
