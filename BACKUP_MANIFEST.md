# Backup manifest

This document records exactly what was saved, where it was uploaded, and how to
restore it. Everything below was produced on 2026-10-21 (UTC) from the
`/workspaces/Yamaha-` workspace.

## What was saved

| Area | Source | Where in the archive |
| --- | --- | --- |
| Project files | `/workspaces/Yamaha-` (including full `.git` history) | `project/` |
| Kilo chat history | `~/.local/share/kilo/kilo.db` (SQLite snapshot, consistent copy) | `kilo/kilo.db` |
| Kilo session artifacts | `~/.local/share/kilo/storage` | `kilo/storage/` |
| Kilo logs | `~/.local/share/kilo/log` | `kilo/log/` |
| Kilo git snapshots | `~/.local/share/kilo/snapshot` | `kilo/snapshot/` |
| Kilo global config | `~/.config/kilo` | `kilo/config/kilo/` |
| Fusion project state | `/workspaces/Yamaha-/.fusion` | `fusion/project-fusion/` |
| Fusion global state | `~/.fusion` (agent sessions, settings, embedded Postgres) | `fusion/home-fusion/` |
| Checksums | all files in the archive | `SHA256SUMS.txt` |

Chat transcripts were additionally exported in human-readable form into
`kilo-sessions/` in this repository (one `.md` transcript plus one raw `.json`
per Kilo session, indexed by `kilo-sessions/README.md`).

## Secrets deliberately excluded

The archive never contains credentials:

- `~/.fusion/agent/auth.json` (provider API keys) is deleted from the archive.
- `*.pem` and `*.key` files under the Fusion state are deleted.
- `~/.ssh` is not part of the archive.
- The repository itself only contains `deploy/examples/.env.example`, a
  template with no real values.

## Where it was uploaded

| Item | Destination |
| --- | --- |
| Repository files, history, branches | `https://github.com/ddipo0522-dev/Yamaha-` (`main`, `mission/M-MVHXN58A-0001-S7HJ`) |
| Readable chat transcripts | `kilo-sessions/` folder in the same repository |
| Full environment archive | GitHub release `backup-2026-10-21` on the same repository |

Release asset: `yamaha-full-backup-<UTC timestamp>.tar.gz`, with a matching
`.sha256` sidecar file.

## Restoring

Restore the project and its history:

```bash
git clone https://github.com/ddipo0522-dev/Yamaha-
cd Yamaha-
git checkout main
```

Restore the full environment archive:

```bash
gh release download backup-2026-10-21 --repo ddipo0522-dev/Yamaha- \
  --pattern 'yamaha-full-backup-*.tar.gz*'
sha256sum -c yamaha-full-backup-*.tar.gz.sha256
tar -xzf yamaha-full-backup-*.tar.gz
```

Then copy the parts back where they belong:

```bash
cp -a yamaha-full-backup-*/project/. /workspaces/Yamaha-/
cp -a yamaha-full-backup-*/kilo/kilo.db ~/.local/share/kilo/kilo.db
cp -a yamaha-full-backup-*/kilo/storage ~/.local/share/kilo/storage
cp -a yamaha-full-backup-*/kilo/log ~/.local/share/kilo/log
cp -a yamaha-full-backup-*/kilo/snapshot ~/.local/share/kilo/snapshot
cp -a yamaha-full-backup-*/kilo/config/kilo ~/.config/kilo
cp -a yamaha-full-backup-*/fusion/home-fusion ~/.fusion
```

Note: `fusion/home-fusion/embedded-postgres` is a raw copy of a live Postgres
data directory taken while the service was running. It is included for
completeness, but it must be validated (or re-seeded) before it is trusted as
a starting cluster.

## Rebuilding the archive

The backup is reproducible from the machine state with a single script; the
export and archive steps used for this backup are:

```bash
python3 /tmp/kilo/export_sessions.py /workspaces/Yamaha-/kilo-sessions   # chat transcripts
bash /tmp/kilo/backup_all.sh                                            # full archive
```

## Verification

- Test suite at backup time: `python3 -m pytest -q` → 23 passed.
- `SHA256SUMS.txt` inside the archive lists a checksum for every archived file.
- The archive sidecar `.sha256` covers the archive itself.
