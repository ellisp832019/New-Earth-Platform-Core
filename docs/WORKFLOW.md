# Branch, PR and Release Workflow

## Start a change

```powershell
git switch main
git pull
git switch -c feature/platform-core-v0.1-foundation
```

## During development

```powershell
new-earth-platform validate
new-earth-platform doctor
new-earth-platform impact <changed-project-id>
pytest
ruff check src tests
mypy src
git status
git add .
git commit -m "feat(platform): establish platform core foundation"
git push -u origin feature/platform-core-v0.1-foundation
```

Open a pull request to `main`.

## Before merge

Required:

- CI green;
- schemas valid;
- dependency references valid;
- compatibility requirements parse;
- declared impact reviewed where relevant;
- tests pass;
- architecture impact documented where required;
- no unexpected generated files;
- no secrets.

## After merge

```powershell
git switch main
git pull
git branch -d feature/platform-core-v0.1-foundation
```

Then create the next repository-specific integration branch.

Suggested next branches:

- NEOS: `feature/neos-platform-core-integration`
- Command Centre: `feature/command-centre-platform-registry`
- Gaia: `feature/gaia-platform-context`
