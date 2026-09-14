#!/usr/bin/env python3
"""tstudy — exam accountability dashboard.

One screen: live timer, recall-forced log, mastery board.
Storage (~/.study, same schema as v1 so old sessions carry over):
  plans.json, active.json, sessions.jsonl
CLI quick paths still work for scripts: tstudy chem 25 / stop / stats.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------- storage ---


def home() -> Path:
    return Path(os.environ.get("STUDY_HOME", str(Path.home() / ".study")))


def _plans_file() -> Path:
    return home() / "plans.json"


def _sessions_file() -> Path:
    return home() / "sessions.jsonl"


def _active_file() -> Path:
    return home() / "active.json"


def ensure() -> None:
    home().mkdir(parents=True, exist_ok=True)
    if not _plans_file().exists():
        _plans_file().write_text("[]")
    if not _sessions_file().exists():
        _sessions_file().write_text("")


def load_plans() -> list:
    ensure()
    try:
        return json.loads(_plans_file().read_text() or "[]")
    except json.JSONDecodeError:
        return []


def load_sessions() -> list:
    ensure()
    out = []
    for line in _sessions_file().read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def active_info() -> dict | None:
    ensure()
    if not _active_file().exists():
        return None
    try:
        return json.loads(_active_file().read_text())
    except json.JSONDecodeError:
        return None


def last_cue() -> tuple[str, int]:
    plans = load_plans()
    if plans:
        return plans[-1].get("subject", "chem"), int(plans[-1].get("mins", 25))
    return "chem", 25


def start_session(subject: str, mins: int, goal: str = "") -> dict:
    """Begin a focus block. Raises RuntimeError if one is already running."""
    ensure()
    if _active_file().exists():
        raise RuntimeError("already in session — stop it first")
    subject = (subject or "").strip() or last_cue()[0]
    mins = mins or last_cue()[1]
    rec = {"subject": subject, "planned_mins": mins,
           "goal": (goal or "").strip(), "start": time.time()}
    _active_file().write_text(json.dumps(rec))
    return rec


def stop_session(recall: int, note: str) -> dict:
    """Close the running block with retrieval proof. Raises on bad input."""
    ensure()
    act = active_info()
    if act is None:
        raise RuntimeError("no active session")
    if recall not in (1, 2, 3, 4):
        raise ValueError("recall must be 1-4")
    note = (note or "").strip()
    if not note:
        raise ValueError("one line of recall required — timer alone doesn't count")
    end = time.time()
    rec = {"subject": act["subject"], "planned_mins": act["planned_mins"],
           "actual_mins": round((end - act["start"]) / 60, 2),
           "recall": recall, "note": note, "goal": act.get("goal", ""),
           "start": act["start"], "end": end, "day": date.today().isoformat()}
    with open(_sessions_file(), "a") as f:
        f.write(json.dumps(rec) + "\n")
    _active_file().unlink()
    return rec


def stats_by_subject() -> dict:
    by: dict = {}
    for s in load_sessions():
        d = by.setdefault(s["subject"], {"n": 0, "mins": 0.0, "rec": 0})
        d["n"] += 1
        d["mins"] += float(s.get("actual_mins", 0))
        d["rec"] += int(s.get("recall", 0))
    for subj, d in by.items():
        d["avg"] = d["rec"] / d["n"] if d["n"] else 0.0
        d["level"] = int(d["mins"] // 25 + d["rec"] // 10)
        d["bar"] = "●" * round(d["avg"]) + "○" * (4 - round(d["avg"]))
    return by


def _config_file() -> Path:
    return home() / "config.json"


def load_config() -> dict:
    ensure()
    try:
        return json.loads(_config_file().read_text() or "{}")
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(cfg: dict) -> None:
    ensure()
    _config_file().write_text(json.dumps(cfg, indent=2))


def available_themes() -> list:
    try:
        from textual.theme import BUILTIN_THEMES
        return sorted(BUILTIN_THEMES)
    except ImportError:
        return ["textual-dark", "textual-light", "dracula", "nord", "gruvbox"]


def get_theme() -> str:
    return load_config().get("theme", "textual-dark")


def set_theme(name: str) -> str:
    names = available_themes()
    if name not in names:
        raise ValueError(f"unknown theme {name!r} — pick from: {', '.join(names)}")
    cfg = load_config()
    cfg["theme"] = name
    save_config(cfg)
    return name


def delete_sessions(indices: list) -> list:
    """Delete file-order rows by 0-based index. Returns deleted records."""
    ensure()
    lines = _sessions_file().read_text().splitlines()
    kill = set(indices)
    if any(i < 0 or i >= len(lines) for i in kill):
        raise IndexError(f"session number out of range (1-{len(lines)})")
    kept, gone = [], []
    for i, line in enumerate(lines):
        (gone if i in kill else kept).append(line)
    _sessions_file().write_text("\n".join(kept) + ("\n" if kept else ""))
    out = []
    for line in gone:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


def resolve_subject_mins(a) -> tuple:
    s = getattr(a, "subject", None) or getattr(a, "pos_subject", None)
    m = getattr(a, "mins", None) or getattr(a, "pos_mins", None)
    return s, m


# ------------------------------------------------------------------- CLI ---


def cmd_plan(a) -> None:
    subject, mins = resolve_subject_mins(a)
    if not subject:
        print("usage: tstudy plan chem [25]", file=sys.stderr)
        sys.exit(1)
    plans = load_plans()
    plans.append({"at": getattr(a, "at", "19:00"),
                  "where": getattr(a, "where", "dorm"),
                  "subject": subject, "mins": mins or 25,
                  "created": time.time()})
    _plans_file().write_text(json.dumps(plans, indent=2))
    print(f"cued: {mins or 25}min {subject}")


def cmd_now(a) -> None:
    subject, mins = resolve_subject_mins(a)
    if not subject or not mins:
        cue_s, cue_m = last_cue()
        subject = subject or cue_s
        mins = mins or cue_m
    try:
        start_session(subject, mins or 2, getattr(a, "goal", ""))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"start: {mins or 2}min {subject}")
    print("phone facedown, 1 tab. Just 2 min.")


def cmd_stop(a) -> None:
    recall = getattr(a, "recall", None)
    note = getattr(a, "note", None)
    if recall is None:
        try: recall = int(input("recall 1-4 (1=foggy 4=teach it): ").strip())
        except (EOFError, ValueError): recall = None
    if note is None:
        try: note = input("one line — what do you remember? ").strip()
        except EOFError: note = None
    try:
        rec = stop_session(recall, note or "")
    except (RuntimeError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"logged: {rec['actual_mins']}min {rec['subject']} recall={rec['recall']}/4")


def cmd_stats(a) -> None:
    by = stats_by_subject()
    if not by:
        print("no sessions yet — run tstudy and hit Start")
        return
    print(f"{'subject':<10}{'n':>4}{'mins':>8}  recall  mastery")
    for subj, d in sorted(by.items()):
        print(f"{subj:<10}{d['n']:>4}{d['mins']:>8.1f}  {d['bar']} {d['avg']:.1f}/4  lv{d['level']}")
    ss = load_sessions()
    print(f"{len({s.get('day') for s in ss})} days · {len(ss)} sessions")


def _describe(s: dict) -> str:
    return (f"{s.get('actual_mins', 0):.1f}m {s.get('subject', '?')} "
            f"★{s.get('recall', 0)} — {s.get('note', '')}")


def cmd_delete(a) -> None:
    ss = load_sessions()
    if not ss:
        print("nothing to delete")
        return
    raw = list(getattr(a, "nums", None) or [])
    if not raw:
        for i, s in enumerate(ss, 1):
            print(f"{i}) {_describe(s)}")
        try:
            raw = input("delete which? (numbers, blank=cancel) ").split()
        except EOFError:
            return
        if not raw:
            return
    try:
        idxs = sorted({int(x) - 1 for x in raw}, reverse=True)
    except ValueError:
        print("numbers only, e.g. tstudy delete 2", file=sys.stderr)
        sys.exit(1)
    if any(i < 0 or i >= len(ss) for i in idxs):
        print(f"out of range — sessions are 1-{len(ss)}", file=sys.stderr)
        sys.exit(1)
    if not getattr(a, "yes", False):
        for i in sorted(idxs):
            print(f"  x {i + 1}) {_describe(ss[i])}")
        try:
            ok = input(f"delete {len(idxs)} session(s)? [y/N] ").strip().lower()
        except EOFError:
            return
        if ok not in ("y", "yes"):
            print("kept everything")
            return
    gone = delete_sessions(idxs)
    print(f"deleted {len(gone)} session(s)")


def cmd_theme(a) -> None:
    names = available_themes()
    name = getattr(a, "name", None)
    if not name:
        print(f"current: {get_theme()}")
        print("pick from: " + ", ".join(names))
        return
    try:
        set_theme(name)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"theme: {name}")


# ------------------------------------------------------------- dashboard ---


def create_app():
    """Build the Textual dashboard app. Imported lazily so CLI works bare."""
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.widgets import Button, DataTable, Footer, Header, Input, Label, ProgressBar, Static
    APP_CSS = """
    #main { height: 1fr; }
    #session { width: 38; border: solid $primary; padding: 1 2; }
    #board { width: 1fr; border: solid $primary; padding: 1 2; margin-left: 1; }
    #setup, #live, #finish { height: auto; }
    #recall-row { height: 3; margin-bottom: 1; }
    .panel-title { text-style: bold; color: $accent; margin-bottom: 1; }
    #timer { text-style: bold; margin: 1 0; }
    #live-sub { color: $text-muted; margin-bottom: 1; }
    .recall-btn { width: 7; min-width: 7; margin-right: 1; }
    #form-error { color: $error; margin-top: 1; }
    #recent-table { height: auto; margin-top: 1; }
    Input { margin-bottom: 1; }
    """

    class StudyApp(App):
        TITLE = "tstudy"
        SUB_TITLE = "exam accountability"
        CSS = APP_CSS
        BINDINGS = [("s", "toggle", "start / stop"), ("t", "cycle_theme", "theme"),
                    ("d", "delete_recent", "delete"), ("q", "quit", "quit")]

        def __init__(self) -> None:
            super().__init__()
            self.recall: int | None = None
            self._ticks = 0
            self._recent_idx: list = []
            self._pending_delete: int | None = None

        def compose(self) -> ComposeResult:
            yield Header()
            with Horizontal(id="main"):
                with Vertical(id="session"):
                    yield Label("SESSION", classes="panel-title")
                    with Vertical(id="setup"):
                        yield Label("subject")
                        yield Input(id="subject")
                        yield Label("minutes")
                        yield Input(id="mins")
                        yield Label("goal (one line, optional)")
                        yield Input(id="goal")
                        yield Button("▶ Start", id="start-btn", variant="success")
                    with Vertical(id="live"):
                        yield Static("--", id="timer")
                        yield ProgressBar(total=100, id="progress")
                        yield Static("", id="live-sub")
                        yield Button("■ Stop — log it", id="stop-btn", variant="warning")
                    with Vertical(id="finish"):
                        yield Label("recall? (must pick one)")
                        yield Label("1 foggy·2 shaky·3 solid·4 teach")
                        with Horizontal(id="recall-row"):
                            yield Button("1", id="r1", classes="recall-btn")
                            yield Button("2", id="r2", classes="recall-btn")
                            yield Button("3", id="r3", classes="recall-btn")
                            yield Button("4", id="r4", classes="recall-btn")
                        yield Label("what do you remember? (required)")
                        yield Input(id="note")
                        yield Static("", id="form-error")
                        with Horizontal():
                            yield Button("✓ Log session", id="log-btn", variant="primary")
                            yield Button("back", id="cancel-btn")
                with Vertical(id="board"):
                    yield Label("MASTERY", classes="panel-title")
                    yield DataTable(id="stats-table", zebra_stripes=True)
                    yield Label("RECENT (d deletes)", classes="panel-title")
                    yield DataTable(id="recent-table", cursor_type="row")
            yield Footer()

        def on_mount(self) -> None:
            try:
                self.theme = get_theme()
            except Exception:
                pass
            cue_s, cue_m = last_cue()
            self.query_one("#subject", Input).value = cue_s
            self.query_one("#mins", Input).value = str(cue_m)
            table = self.query_one("#stats-table", DataTable)
            table.add_column("subject")
            table.add_column("n")
            table.add_column("mins")
            table.add_column("recall")
            table.add_column("lv")
            recent = self.query_one("#recent-table", DataTable)
            recent.add_column("#")
            recent.add_column("session")
            self.refresh_all()
            self.set_interval(1.0, self.tick)

        # -- state -> widgets --
        def _mode(self) -> str:
            if active_info() is None:
                return "setup"
            if self.query_one("#finish", Vertical).display:
                return "finish"
            return "live"

        def _render_mode(self) -> None:
            mode = self._mode()
            self.query_one("#setup", Vertical).display = mode == "setup"
            self.query_one("#live", Vertical).display = mode == "live"
            self.query_one("#finish", Vertical).display = mode == "finish"

        def refresh_all(self) -> None:
            self._render_mode()
            by = stats_by_subject()
            table = self.query_one("#stats-table", DataTable)
            table.clear()
            for subj, d in sorted(by.items()):
                table.add_row(subj, str(d["n"]), f"{d['mins']:.1f}",
                              f"{d['bar']} {d['avg']:.1f}", f"lv{d['level']}")
            ss = load_sessions()
            days = len({s.get("day") for s in ss})
            self.sub_title = f"{days} days · {len(ss)} sessions"
            recent = self.query_one("#recent-table", DataTable)
            recent.clear()
            self._recent_idx = []
            for i in range(len(ss) - 1, max(len(ss) - 6, -1), -1):
                s = ss[i]
                self._recent_idx.append(i)
                recent.add_row(str(i + 1),
                    f"{s.get('actual_mins', 0):.1f}m {s.get('subject', '?')} "
                    f"{'★' * int(s.get('recall', 0))} — {s.get('note', '')}")
            if not self._recent_idx:
                recent.add_row("–", "nothing logged yet — hit Start")

        def tick(self) -> None:
            act = active_info()
            if act is None:
                return
            el = time.time() - act["start"]
            plan = float(act.get("planned_mins", 25)) * 60
            em, es = int(el // 60), int(el % 60)
            pm, ps = int(plan // 60), int(plan % 60)
            if el < plan:
                left = plan - el
                txt = (f"{em:02d}:{es:02d} / {pm:02d}:{ps:02d}\n"
                       f"-{int(left // 60):02d}:{int(left % 60):02d} left · {act['subject']}")
                pct = el / plan * 100 if plan else 0
            else:
                over = el - plan
                txt = (f"{em:02d}:{es:02d} / {pm:02d}:{ps:02d}\n"
                       f"+{int(over // 60):02d}:{int(over % 60):02d} over · {act['subject']}")
                pct = 100.0
            self.query_one("#timer", Static).update(txt)
            self.query_one("#progress", ProgressBar).update(progress=pct)
            goal = (act.get("goal") or "").strip()
            self.query_one("#live-sub", Static).update(
                f"goal: {goal}" if goal else "phone facedown, 1 tab.")
            self._ticks += 1
            if self._ticks % 5 == 0:
                self.refresh_all()

        # -- actions --
        def action_toggle(self) -> None:
            if active_info() is None:
                self.do_start()
            else:
                self.query_one("#finish", Vertical).display = True
                self._render_mode()

        def action_cycle_theme(self) -> None:
            names = available_themes()
            cur = get_theme()
            nxt = names[(names.index(cur) + 1) % len(names)] if cur in names else names[0]
            self.theme = nxt
            cfg = load_config()
            cfg["theme"] = nxt
            save_config(cfg)
            self.notify(f"theme: {nxt}")

        def action_delete_recent(self) -> None:
            if not self._recent_idx:
                self.notify("nothing to delete")
                return
            table = self.query_one("#recent-table", DataTable)
            try:
                pos = table.cursor_row
            except Exception:
                pos = 0
            if pos < 0 or pos >= len(self._recent_idx):
                return
            idx = self._recent_idx[pos]
            if self._pending_delete == idx:
                self._pending_delete = None
                try:
                    gone = delete_sessions([idx])
                except IndexError as e:
                    self.notify(str(e), severity="error")
                    return
                self.refresh_all()
                self.notify(f"deleted {_describe(gone[0])}" if gone else "deleted")
            else:
                ss = load_sessions()
                self._pending_delete = idx
                self.notify(f"press d again to delete {idx + 1}) {_describe(ss[idx])}")

        def do_start(self) -> None:
            cue_s, cue_m = last_cue()
            subject = self.query_one("#subject", Input).value.strip() or cue_s
            try:
                mins = int(self.query_one("#mins", Input).value.strip() or cue_m)
            except ValueError:
                mins = cue_m
            goal = self.query_one("#goal", Input).value.strip()
            try:
                start_session(subject, mins, goal)
            except RuntimeError as e:
                self.notify(str(e), severity="error")
                return
            self.recall = None
            self.query_one("#note", Input).value = ""
            self.refresh_all()
            self.tick()

        def do_log(self) -> None:
            err = self.query_one("#form-error", Static)
            if self.recall is None:
                err.update("pick recall 1-4 first")
                return
            note = self.query_one("#note", Input).value.strip()
            if not note:
                err.update("one line of recall required")
                return
            try:
                rec = stop_session(self.recall, note)
            except (RuntimeError, ValueError) as e:
                err.update(str(e))
                return
            err.update("")
            self.recall = None
            for i in (1, 2, 3, 4):
                self.query_one(f"#r{i}", Button).variant = "default"
            self.refresh_all()
            self.notify(f"logged {rec['actual_mins']}min {rec['subject']} ★{rec['recall']}")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            bid = event.button.id or ""
            if bid == "start-btn":
                self.do_start()
            elif bid == "stop-btn":
                self.query_one("#finish", Vertical).display = True
                self._render_mode()
            elif bid == "cancel-btn":
                self.query_one("#finish", Vertical).display = False
                self._render_mode()
            elif bid == "log-btn":
                self.do_log()
            elif bid in ("r1", "r2", "r3", "r4"):
                self.recall = int(bid[1])
                for i in (1, 2, 3, 4):
                    self.query_one(f"#r{i}", Button).variant = (
                        "success" if i == self.recall else "default")
                self.query_one("#form-error", Static).update("")

    return StudyApp()


def launch_dashboard() -> None:
    try:
        app = create_app()
    except ImportError:
        print("dashboard needs Textual: pip3 install textual", file=sys.stderr)
        sys.exit(1)
    app.run()


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="tstudy")
    sub = p.add_subparsers(dest="cmd")
    pp = sub.add_parser("plan", help="save a cue: tstudy plan chem [25]")
    pp.add_argument("pos_subject", nargs="?", default=None)
    pp.add_argument("pos_mins", nargs="?", type=int, default=None)
    pp.add_argument("--at", default="19:00")
    pp.add_argument("--where", default="dorm")
    pp.add_argument("--subject", default=None)
    pp.add_argument("--mins", type=int, default=None)
    pp.set_defaults(fn=cmd_plan)
    for name in ("now", "start"):
        pn = sub.add_parser(name, help="quick start: tstudy chem [25]")
        pn.add_argument("pos_subject", nargs="?", default=None)
        pn.add_argument("pos_mins", nargs="?", type=int, default=None)
        pn.add_argument("--subject", default=None)
        pn.add_argument("--mins", type=int, default=None)
        pn.add_argument("--goal", default="")
        pn.set_defaults(fn=cmd_now)
    pt = sub.add_parser("stop", help="stop and log")
    pt.add_argument("--recall", type=int, default=None)
    pt.add_argument("--note", default=None)
    pt.set_defaults(fn=cmd_stop)
    pv = sub.add_parser("stats", help="mastery per subject")
    pv.set_defaults(fn=cmd_stats)
    pd = sub.add_parser("delete", help="delete sessions: tstudy delete [N] [--yes]")
    pd.add_argument("nums", nargs="*", default=[])
    pd.add_argument("--yes", action="store_true")
    pd.set_defaults(fn=cmd_delete)
    ph = sub.add_parser("theme", help="list or set theme: tstudy theme [name]")
    ph.add_argument("name", nargs="?", default=None)
    ph.set_defaults(fn=cmd_theme)
    pm = sub.add_parser("menu", help="open dashboard")
    pm.set_defaults(fn=lambda a: launch_dashboard())
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        if sys.stdin.isatty():
            return launch_dashboard()
        return cmd_now(argparse.Namespace(subject=None, mins=None, goal=""))
    if argv and argv[0] not in ("plan", "now", "start", "stop", "stats", "menu",
                                "delete", "theme", "-h", "--help"):
        argv = ["now"] + argv
    a = p.parse_args(argv)
    if not getattr(a, "cmd", None):
        if sys.stdin.isatty():
            return launch_dashboard()
        return cmd_now(a)
    a.fn(a)


if __name__ == "__main__":
    main()
