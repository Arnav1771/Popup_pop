# CmdPop Decisions

**Current Sprint:** Sprint 0 (Planning complete)

**All architectural decisions are recorded in:**
→ **[`docs/sprint0/DECISIONS.md`](docs/sprint0/DECISIONS.md)**

---

## Quick Reference

16 core decisions have been made:

| ID | Title | Status |
|----|-------|--------|
| D-001 | Database Technology (SQLite) | ✅ DECIDED |
| D-002 | Hotkey Listener (pynput) | ✅ DECIDED |
| D-003 | Architecture: Daemon vs One-Shot | ✅ DECIDED |
| D-004 | TUI Framework (Textual) | ✅ DECIDED |
| D-005 | Fuzzy Search Algorithm (RapidFuzz) | ✅ DECIDED |
| D-006 | Shell History Integration (no plugins) | ✅ DECIDED |
| D-007 | Command Injection Strategy (platform-specific) | ✅ DECIDED |
| D-008 | Database Schema & Deduplication | ✅ DECIDED |
| D-009 | Configuration Format (TOML) | ✅ DECIDED |
| D-010 | Ranking Formula (3-factor scoring) | ✅ DECIDED |
| D-011 | Supported Shells (Bash, Zsh, Fish, PowerShell, CMD) | ✅ DECIDED |
| D-012 | Sensitive Command Filtering | ✅ DECIDED |
| D-013 | Logging & Debugging | ✅ DECIDED |
| D-014 | Testing Strategy (multi-level) | ✅ DECIDED |
| D-015 | Packaging & Distribution (PyPI via pipx) | ✅ DECIDED |
| D-016 | CI/CD Pipeline (GitHub Actions matrix) | ✅ DECIDED |

**All decisions are DECIDED. No OPEN decisions.**

---

## Adding New Decisions

When a new architectural decision must be made:

1. **Create entry in `docs/sprint0/DECISIONS.md`** with next ID (D-017, etc.)
2. **Format:** Use the decision template (Q→D→A→R→Status)
3. **Update this file** with new entry in table above
4. **Link in PR** to decision for reviewers

---

## Viewing Decisions

```bash
# Read in terminal
cat docs/sprint0/DECISIONS.md

# Or view online
# https://github.com/Arnav1771/Popup_pop/blob/main/docs/sprint0/DECISIONS.md
```

---

> CmdPop · All decisions in `docs/sprint0/DECISIONS.md`
