cat > /workspaces/codespaces-blank/pseudohunter/README.md << 'EOF'
# PseudoHunter

> OSINT pseudo generator — by thejazzman ft. Claude

PseudoHunter automatically generates username variants from a first and last name, then searches them across hundreds of platforms using Sherlock and/or Maigret.

## Features

- 50+ generated variants (dots, underscores, dashes, vowel removal, truncations...)
- Automatic filter for usernames under 5 characters
- Sherlock (300+ sites) and Maigret (2500+ sites)
- 8 parallel threads
- Real-time progress bar with live hit counter
- Interactive mode

## Requirements

- Python 3.8+
- Sherlock
- Maigret

## Installation

\`\`\`bash
git clone https://github.com/lheoofficiel-create/pseudo_hunter
cd pseudo_hunter
pip3 install sherlock-project maigret --break-system-packages
pip3 install urllib3==1.26.18 --break-system-packages
\`\`\`

## Usage

\`\`\`bash
python3 pseudo_hunter.py
\`\`\`

The program will ask:

\`\`\`
Enter first name : John
Enter last name  : Smith

  48 pseudos available (>=5 characters)

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

## Generated variants examples

For John Smith:

| Variant | Logic |
|---|---|
| john.smith | firstname.lastname |
| jsmith | initial+lastname |
| smth.john | consonants(lastname).firstname |
| j.smith | initial.lastname |
| john.smt | firstname+truncation |
| jhn.smith | consonants(firstname).lastname |

## Legal disclaimer

This tool is intended for **legal, educational and ethical use only**.

- Only use it on your own accounts or with explicit permission from the target
- Using this tool on unauthorized targets may be illegal in your country
- The authors take no responsibility for any misuse

## Authors

- **thejazzman** — design & development
- **Claude (Anthropic)** — development assistance
EOF

cd /workspaces/codespaces-blank/pseudohunter
git add README.md
git commit -m "Add English README"
git push
