# tstudy

Exam accountability dashboard. One screen: live timer, recall-forced log, mastery board.

```
plan (cue) → start (tiny 2-min default) → focus → stop (recall 1-4 + 1 line) → stats (mastery)
```

Science: Fogg `B = M × A × T` (tiny start + clear cue), SDT competence
(levels/recall, not shame), retrieval practice (no log without a recall note).

## Install

```sh
pip install -r requirements.txt
ln -sf "$PWD/tstudy.py" ~/.local/bin/tstudy   # ensure ~/.local/bin is on PATH
```

## Use

| Type | What happens |
|---|---|
| `tstudy` | Dashboard: Start → live `00:03 / 25:00` timer → Stop → pick recall 1-4 + note → Log. Keys: `s` start/stop, `t` theme, `d` delete, `q` quit. Click out of text fields first or letters type instead. |
| `tstudy chem 25` | Quick start without the dashboard. Omit mins → last plan, omit all → 2min general. |
| `tstudy stop` | Stop + log (prompts recall + note). |
| `tstudy stats` | Mastery table in plain text. |
| `tstudy delete [N] [--yes]` | Numbered list, pick what goes (blank=cancel). Dashboard: cursor the RECENT row, `d` twice. |
| `tstudy theme [name]` | Lists 21 themes + current; with name sets it (saved to `~/.study/config.json`). Dashboard `t` cycles. |
| `tstudy plan chem 25` | Save cue so the dashboard pre-fills subject/mins. |

## Data

`~/.study/` — `plans.json`, `active.json`, `sessions.jsonl`, `config.json`.
Override for tests: `STUDY_HOME=/tmp/x tstudy stats`.
One session at a time. Logging requires recall 1-4 + note.
