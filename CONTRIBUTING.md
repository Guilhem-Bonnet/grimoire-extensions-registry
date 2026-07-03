# Contribuer au registry

Merci de vouloir publier une extension ou un blueprint. Le marketplace n'est
pas un annuaire : chaque contribution s'ancre sur le
[catalogue de patterns agentiques](https://github.com/Guilhem-Bonnet/grimoire-forge)
et respecte des règles non négociables.

## Créer une extension

Partez du
[template officiel](https://github.com/Guilhem-Bonnet/grimoire-extension-template)
(« Use this template ») : manifeste pré-rempli, skill d'exemple, script de
vérification et CI qui rejoue le cycle `add/verify/remove` à chaque push.

Testez le cycle complet en local avant de publier :

```bash
pip install grimoire-kit
grimoire ext add . && grimoire ext verify <id> && grimoire ext remove <id>
```

## Publier

```bash
git clone https://github.com/Guilhem-Bonnet/grimoire-extensions-registry
grimoire ext publish <votre-extension>/ --registry grimoire-extensions-registry
cd grimoire-extensions-registry
bash scripts/publish-pr.sh <id> <version>
```

Le script ouvre une PR avec la checklist de revue. L'archive est
déterministe : ne modifiez jamais un `dist/*.tar.gz` à la main.

## Ce que la CI vérifie (bloquant)

- Index conforme au schéma (`registry.schema.json`).
- Checksum sha256 de chaque archive et de chaque blueprint.
- Manifeste de chaque archive : structure complète, `patterns.implements`
  non vide, chemins relatifs sans remontée, permissions valides,
  `kind` dans l'enum (`flow-adapter`, `mcp-toolbox`, `observability`,
  `capability`).
- Cohérence id/version entre l'index et le contenu.

## Ce que la revue humaine vérifie (contributions tierces)

- Les **scripts d'installation** : rien hors du périmètre déclaré, pas de
  téléchargement opaque, pas d'écriture hors des surfaces gouvernées.
- Les **permissions** déclarées couvrent ce que font réellement les scripts.
- Tout **hook** s'enregistre en mode `shadow` — un script qui tente un autre
  mode est refusé.
- La **description** et le mapping patterns sont honnêtes : l'extension fait
  ce qu'elle annonce.

Les extensions des mainteneurs passent en fast-track (CI seule) ; les
contributions tierces exigent une revue approuvée avant merge.

## Versions

Semver. Une republication de version identique remplace l'entrée (réservée
aux mainteneurs pour correction immédiate) ; toute évolution de contenu
passe par un bump. Les anciennes versions restent installables
(`--version X.Y.Z`).
