#!/usr/bin/env bash
# Ouvre une PR de publication après `grimoire ext publish --registry <ce repo>`.
#
# Usage : bash scripts/publish-pr.sh <extension-id> <version>
# Prérequis : gh authentifié, publication déjà faite dans le clone courant.

set -euo pipefail

EXT_ID="${1:?usage: publish-pr.sh <extension-id> <version>}"
VERSION="${2:?usage: publish-pr.sh <extension-id> <version>}"
BRANCH="publish/${EXT_ID}-${VERSION}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if git diff --quiet -- registry.json "dist/${EXT_ID}-${VERSION}.tar.gz" 2>/dev/null \
   && ! git status --porcelain -- "dist/${EXT_ID}-${VERSION}.tar.gz" | grep -q .; then
    echo "Rien à publier : lancer d'abord 'grimoire ext publish ... --registry ${REPO_ROOT}'" >&2
    exit 1
fi

git checkout -b "$BRANCH"
git add registry.json "dist/${EXT_ID}-${VERSION}.tar.gz"
git commit -m "publish: ${EXT_ID} ${VERSION}"
git push -u origin "$BRANCH"
gh pr create \
    --title "publish: ${EXT_ID} ${VERSION}" \
    --body "Publication de \`${EXT_ID}\` ${VERSION} via \`grimoire ext publish\`.

- [ ] CI validate-registry verte
- [ ] Revue des scripts d'installation et permissions (extensions tierces)"
git checkout main
echo "PR ouverte pour ${EXT_ID} ${VERSION} (branche ${BRANCH})."
