#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[+] Mise à jour des paquets..."
sudo apt update

echo "[+] Installation de Python et pip..."
sudo apt install -y python3 python3-pip wget tar

echo "[+] Installation de Sherlock..."
pip3 install --upgrade sherlock-project

echo "[+] Installation de Maigret..."
pip3 install --upgrade maigret

echo "[+] Installation de Holehe..."
pip3 install --upgrade holehe

echo "[+] Installation de PhoneInfoga..."

LATEST=$(curl -s https://api.github.com/repos/sundowndev/phoneinfoga/releases/latest | grep tag_name | cut -d '"' -f4)

wget -O /tmp/phoneinfoga.tar.gz \
"https://github.com/sundowndev/phoneinfoga/releases/download/${LATEST}/phoneinfoga_Linux_x86_64.tar.gz"

sudo mkdir -p /opt/phoneinfoga
sudo tar -xzf /tmp/phoneinfoga.tar.gz -C /opt/phoneinfoga

sudo chmod +x /opt/phoneinfoga/phoneinfoga
sudo ln -sf /opt/phoneinfoga/phoneinfoga /usr/local/bin/phoneinfoga

echo "[+] PhoneInfoga installé."

echo "[+] Installation de PseudoHunter..."
chmod +x "$SCRIPT_DIR/pseudo_hunter.py"
sudo ln -sf "$SCRIPT_DIR/pseudo_hunter.py" /usr/local/bin/pseudohunter

#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod +x "$SCRIPT_DIR/pseudo_hunter.py"
sudo ln -sf "$SCRIPT_DIR/pseudo_hunter.py" /usr/local/bin/pseudohunter

# Sherlock wrapper
if python3 -c "import sherlock_project" >/dev/null 2>&1; then
cat << 'EOF' | sudo tee /usr/local/bin/sherlock >/dev/null
#!/usr/bin/env bash
python3 -m sherlock_project "$@"
EOF
sudo chmod +x /usr/local/bin/sherlock
fi

# Maigret wrapper
if python3 -c "import maigret" >/dev/null 2>&1; then
cat << 'EOF' | sudo tee /usr/local/bin/maigret >/dev/null
#!/usr/bin/env bash
python3 -m maigret "$@"
EOF
sudo chmod +x /usr/local/bin/maigret
fi

echo "PseudoHunter installed."
echo "Run with: pseudohunter"

echo ""
echo "Installation terminée."
echo ""
echo "Commandes disponibles :"
echo "  pseudohunter"
echo "  sherlock"
echo "  maigret"
echo "  holehe"
echo "  phoneinfoga"