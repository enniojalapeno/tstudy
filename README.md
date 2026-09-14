<h1 align="center">tstudy</h1>

<p align="center">
  Exam accountability for the terminal.<br/>
  Start a timer, prove you remember, watch mastery grow.
</p>

<p align="center">
  <a href="https://github.com/enniojalapeno/tstudy/blob/main/LICENSE"><img src="https://img.shields.io/github/license/enniojalapeno/tstudy?style=flat-square" alt="License" /></a>
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square" alt="Python" />
  <img src="https://img.shields.io/badge/terminal-macOS%20%2F%20Linux-lightgrey?style=flat-square" alt="Platform" />
</p>

---

## Install

```sh
pip install -r requirements.txt
ln -sf "$PWD/tstudy.py" ~/.local/bin/tstudy   # ensure ~/.local/bin is on PATH
```

## How it works

- **Start**: `tstudy` opens the dashboard — subject, minutes, goal → `▶ Start`
- **Focus**: live `00:03 / 25:00` timer with a progress bar
- **Log**: `■ Stop` → pick recall 1–4 → one line of what you remember → `✓ Log`
- **Proof**: logging *requires* recall + note — timer alone doesn't count
- **Delete**: cursor a RECENT row, press `d` twice (or `tstudy delete [N]`)
- **Keys**: `s` start/stop, `t` theme, `d` delete, `q` quit

Quick paths without the dashboard: `tstudy chem 25`, `tstudy stop`, `tstudy stats`, `tstudy plan chem 25`.

## Settings

- **Theme**: 21 builtins — `dracula`, `nord`, `gruvbox`, `catppuccin-mocha`, `tokyo-night`… (`tstudy theme [name]`, saved to `~/.study/config.json`)
- **Data**: `~/.study/` — `plans.json`, `active.json`, `sessions.jsonl`, `config.json`
- **Cue**: `tstudy plan chem 25` pre-fills the dashboard's subject/minutes

## Dev

```sh
git clone https://github.com/enniojalapeno/tstudy.git
cd tstudy
pip install -r requirements.txt
python tstudy.py
```

## License

[MIT](LICENSE)
