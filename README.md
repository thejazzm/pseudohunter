# PseudoHunter

OSINT username hunter — generates username variants from a first/last name and searches across platforms using Sherlock, Maigret, Holehe, and PhoneInfoga.

> Built for legal, educational, and authorized investigation purposes only. See [Responsible Use](#responsible-use) below.

---

## Features

- **Username variant generation**: produces 50+ realistic username candidates from a first and last name (e.g. `john.doe`, `doej`, `j_doe92`)
- **Confidence ranking**: variants are scored and sorted by likelihood of real-world usage, so the most plausible candidates appear first
- **Manual or automatic selection**: pick exact variants by number, or auto-select the top N
- **Multi-tool orchestration**: runs Sherlock and Maigret in parallel (separate thread pools, tuned per tool), plus Holehe (email) and PhoneInfoga (phone) when provided
- **Pre-flight dependency check**: verifies all required external tools are installed before launching a scan — fails fast with a clear message instead of silently returning empty results
- **Time estimation**: estimates scan duration before launch based on variant count and tool selection, with a confirmation prompt for long runs
- **Clean interruption**: Ctrl+C kills all active subprocesses immediately — no orphaned background processes
- **Session journal**: every search attempt (success, timeout, error, tool missing) is logged with timestamps to a separate JSON journal, independent of the results report
- **Google Dorks generation**: auto-generates manual search dorks for the target as a complement to automated tools
- **Export**: results saved as both JSON (structured) and TXT (human-readable) reports

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/thejazzm/pseudohunter.git
cd pseudohunter
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install PhoneInfoga (Go binary, not on PyPI)

Download the latest release for your architecture from the [PhoneInfoga releases page](https://github.com/sundowndev/phoneinfoga/releases), then:

```bash
tar -xzf phoneinfoga_Linux_x86_64.tar.gz
chmod +x phoneinfoga
sudo mv phoneinfoga /usr/local/bin/
```

Verify installation:

```bash
phoneinfoga version
```

### 4. Verify all tools are available

```bash
which sherlock maigret holehe phoneinfoga
```

All four should return a valid path. If one is missing, PseudoHunter will detect it and refuse to launch the corresponding scan mode, rather than failing silently.

---

## Usage

```bash
python3 pseudo_hunter.py
```

You'll be prompted for:

1. **First name / Last name** (required)
2. **Email** (optional — enables Holehe)
3. **Phone number** (optional — enables PhoneInfoga)
4. **Variant selection**: choose `Auto` (take the top N ranked variants) or `Manual` (pick exact numbers from the displayed list)
5. **Search mode**:
   - `1` Sherlock only
   - `2` Maigret only
   - `3` Sherlock + Maigret
   - `4` Full scan (Sherlock + Maigret + Holehe + PhoneInfoga)
   - `5` Generate variants only (no search)

Before launching, PseudoHunter displays an estimated duration for each mode and asks for confirmation on long runs (>10 min).

### Output

- `pseudohunter_<first>_<last>_<timestamp>.json` — structured results
- `pseudohunter_<first>_<last>_<timestamp>.txt` — human-readable report
- `pseudohunter_journal_<timestamp>.json` — session log (every attempt, status, timestamp)

These files are git-ignored by default — never commit real scan data.

---

## Architecture

```
pseudo_hunter.py        Entry point: UI, scan orchestration, export
osint_methodology.py    Methodology helpers: confidence scoring, session journal,
                         dork formatting, cross-tool deduplication
```

PseudoHunter separates Sherlock and Maigret into independent thread pools (Maigret is significantly slower per-target, so it gets a smaller pool to avoid resource contention). Each subprocess is tracked in a global registry and force-killed on interruption.

---

## Methodology

```
First + Last name
    │
    ▼
Variant generation ──► Confidence scoring ──► Manual/Auto selection
    │
    ├──► Sherlock  ──┐
    ├──► Maigret   ──┼──► Deduplicated results
    │                │
Email ──► Holehe      │
Phone ──► PhoneInfoga │
    │                 │
    └─────────────────┴──► JSON + TXT export + Session journal
```

---

## Responsible Use

PseudoHunter is built for:

- Authorized security research and penetration testing
- Personal OSINT footprint audits (checking your own digital exposure)
- Educational use in cybersecurity/OSINT training contexts

It must **not** be used to:

- Investigate, track, or profile individuals without their consent or legal authorization
- Bypass platform terms of service
- Facilitate harassment, stalking, or doxxing

You are responsible for complying with applicable laws (including data protection regulations such as GDPR) in your jurisdiction. The author assumes no liability for misuse.

---

## Roadmap

- [ ] Resume mode for interrupted scans
- [ ] Saved target profiles
- [ ] Confidence score displayed inline in results
- [ ] Cross-tool result deduplication wired into the main report (currently available in `osint_methodology.py`, not yet surfaced in CLI output)

### 5. (Optional) Install as a global command

```bash
./install.sh
```

This lets you run the tool from anywhere with:

```bash
pseudohunter
```

---

## License

MIT — see [LICENSE](LICENSE)
