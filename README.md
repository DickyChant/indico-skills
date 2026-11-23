# indico-skills

Tools for searching CERN Indico talks/slides and CERN GitLab projects, packaged as a Claude Code skill (`.claude/skills/cern-search`).

## Setup

Create `.env` in the repo root (gitignored):

```
TOKEN=<indico.cern.ch personal API token>
GITLAB_TOKEN=<gitlab.cern.ch token with read_api>
GITLAB_USER=<your gitlab username>
```

## Usage

```bash
S=.claude/skills/cern-search/scripts/cern_search.py
python3 -I $S mytalks --grep 'WW'
python3 -I $S indico "Higgs mass" --type attachment --mine
python3 -I $S download <indico attachment url>        # saves to materials/ (gitignored)
python3 -I $S gitlab-projects --search ssww
python3 -I $S gitlab-code "term" --project group/project
```

Or just ask Claude Code in this folder, e.g. "find my talk about X".
