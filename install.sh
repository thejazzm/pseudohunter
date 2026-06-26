#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Updating packages..."
sudo apt update

echo "[+] Installing Python and pip..."
sudo apt install -y python3 python3-pip wget tar

echo "[+] Installing Sherlock..."
pip3 install --upgrade sherlock-project

echo "[+] Installing Maigret..."
pip3 install --upgrade maigret

echo "[+] Installing Holehe..."
pip3 install --upgrade holehe

echo "[+] Installing PhoneInfoga..."
LATEST=$(curl -s https://api.github.com/repos/sundowndev/phoneinfoga/releases/latest | grep tag_name | cut -d '"' -f4)
wget -O /tmp/phoneinfoga.tar.gz \
"https://github.com/sundowndev/phoneinfoga/releases/download/${LATEST}/phoneinfoga_Linux_x86_64.tar.gz"

sudo mkdir -p /opt/phoneinfoga
sudo tar -xzf /tmp/phoneinfoga.tar.gz -C /opt/phoneinfoga
sudo chmod +x /opt/phoneinfoga/phoneinfoga
sudo ln -sf /opt/phoneinfoga/phoneinfoga /usr/local/bin/phoneinfoga
echo "[+] PhoneInfoga installed."

echo "[+] Installing PseudoHunter..."
chmod +x "$SCRIPT_DIR/pseudo_hunter.py"
sudo ln -sf "$SCRIPT_DIR/pseudo_hunter.py" /usr/local/bin/pseudohunter

# Sherlock wrapper (sherlock_project supports -m invocation)
if python3 -c "import sherlock_project" >/dev/null 2>&1; then
cat << 'EOF' | sudo tee /usr/local/bin/sherlock >/dev/null
#!/usr/bin/env bash
python3 -m sherlock_project "$@"
EOF
sudo chmod +x /usr/local/bin/sherlock
fi

# Maigret wrapper (maigret supports -m invocation)
if python3 -c "import maigret" >/dev/null 2>&1; then
cat << 'EOF' | sudo tee /usr/local/bin/maigret >/dev/null
#!/usr/bin/env bash
python3 -m maigret "$@"
EOF
sudo chmod +x /usr/local/bin/maigret
fi

# Holehe wrapper (holehe has NO __main__.py, must call holehe.core:main directly,
# matching its actual console_scripts entry point — this is why `python3 -m holehe`
# does not work, unlike sherlock_project and maigret above)
if python3 -c "import holehe" >/dev/null 2>&1; then
cat << 'EOF' | sudo tee /usr/local/bin/holehe >/dev/null
#!/usr/bin/env python3
import sys
from holehe.core import main
if __name__ == "__main__":
    sys.exit(main())
EOF
sudo chmod +x /usr/local/bin/holehe
fi

echo ""
echo "Installation complete."
echo ""
echo "Available commands:"
echo "  pseudohunter"
echo "  sherlock"
echo "  maigret"
echo "  holehe"
echo "  phoneinfoga"