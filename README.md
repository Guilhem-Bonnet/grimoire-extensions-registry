# Registry d'extensions Grimoire

Index des extensions publiées de Grimoire Forge (modèle Homebrew tap :
un repo git versionné, pas de backend). Chaque extension est un bundle
d'artefacts gouvernés décrit par un manifeste validé, ancré sur le
[catalogue de patterns agentiques](https://github.com/Guilhem-Bonnet/grimoire-forge).

## Structure

| Élément | Rôle |
| --- | --- |
| [registry.json](registry.json) | Index : extensions, versions, checksums, résumés de manifestes |
| [registry.schema.json](registry.schema.json) | Schéma JSON de l'index |
| `dist/` | Archives `tar.gz` déterministes (mtime/uid normalisés) |
| [scripts/validate-registry.py](scripts/validate-registry.py) | CI de conformité |
| `.github/workflows/validate.yml` | Workflow du futur repo dédié |

## Publier

```bash
grimoire ext publish <dossier-extension> --registry <clone-de-ce-repo>
bash scripts/publish-pr.sh mon-extension 0.1.0   # branche + commit + PR
```

La publication échoue si le manifeste est invalide. L'archive est
déterministe : republier une extension inchangée produit le même checksum.

## Installer depuis le registry

```bash
grimoire ext add crewai --registry <clone>              # dernière version
grimoire ext add crewai --registry <clone> --version 0.1.0
```

Le checksum est vérifié avant extraction ; l'extraction refuse tout chemin
absolu ou remontant.

## CI de conformité

```bash
python3 scripts/validate-registry.py --registry . \
  --catalogue <chemin>/catalogue-export.json
```

Vérifie : schéma de l'index, existence et checksum de chaque archive,
manifeste de chaque archive (validation structurelle complète), existence
des patterns déclarés dans le catalogue, permissions cohérentes avec les
hooks fournis.

## Curation

- Extensions internes (mainteneurs) : fast-track — la CI suffit.
- Extensions tierces (via PR) : CI + revue humaine obligatoire des scripts d'installation et des permissions déclarées.
- Règle non négociable : tout hook démarre en mode `shadow` dans le projet hôte.
