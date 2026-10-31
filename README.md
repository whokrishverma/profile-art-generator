# profile-art-generator

Private source repository for generating the artwork displayed in the
`whokrishverma` GitHub profile README.

## Project structure

```text
assets/
  photos/                 Source photos and their .type selectors
generators/
  ascii/                  ASCII portrait generators (all versions)
  heatmap/                Contribution heatmap generator
  info-card/              Profile info-card generator
generated/                Generated SVG outputs (local/workflow artifacts)
.github/workflows/        GitHub Actions automation
CONFIG.py                 Runtime configuration placeholder (no secrets)
```

## GitHub Actions secret

Set `PROFILE_REPO_PAT` in **Settings → Secrets and variables → Actions**.
Never put a personal access token in source code or commit it to the repository.

The workflow generates SVGs and publishes them to the public
`whokrishverma/whokrishverma` profile repository.
