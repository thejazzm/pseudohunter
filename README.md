# PseudoHunter

> OSINT username generator — by thejazzman ft. Claude

PseudoHunter automatically generates username variants from a first and last name, then hunts them across hundreds of platforms using Sherlock and/or Maigret.

---

## Features

- 50+ generated variants per target (dots, underscores, dashes, vowel removal, truncations)
- Automatic filter — ignores usernames under 5 characters
- Sherlock integration — 300+ sites
- Maigret integration — 2500+ sites
- 8 parallel threads for fast execution
- Real-time animated progress bar with live hit counter
- Fully interactive — choose your search depth and tool

---

## Requirements

- Python 3.8+
- Sherlock
- Maigret

---

## Installation

\`\`\`bash
git clone https://github.com/lheoofficiel-create/pseudohunter
cd pseudohunter
pip3 install sherlock-project maigret --break-system-packages
pip3 install urllib3==1.26.18 --break-system-packages
\`\`\`

---

## Usage

\`\`\`bash
python3 pseudo_hunter.py
\`\`\`

\`\`\`
Enter first name : John
Enter last name  : Smith

  48 variants available (>=5 characters)

How many pseudos do you want to use?
(between 1 and 48, or Enter for all)
> 20

Search mode?
  [1] Sherlock only
  [2] Maigret only
  [3] Sherlock + Maigret (full)
  [4] Generate only (no search)
>
\`\`\`

---

## Generated variants — example

| Variant | Logic |
|---|---|
| \`john.smith\` | firstname.lastname |
| \`jsmith\` | initial+lastname |
| \`smth.john\` | consonants(lastname).firstname |
| \`j.smith\` | initial.lastname |
| \`john.smt\` | firstname+truncation |
| \`jhn.smith\` | consonants(firstname).lastname |

---

## Legal disclaimer

This tool is intended for **legal, educational and ethical use only**.  
Only use it on your own accounts or with explicit authorization.  
The authors take no responsibility for any misuse.

---

## Authors

- **thejazzman** — design & development
- **Claude (Anthropic)** — development assistance
