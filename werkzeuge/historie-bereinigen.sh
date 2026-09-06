#!/bin/bash
# Entfernt die echten Albumnamen aus der Git-Historie.
#
#     bash werkzeuge/historie-bereinigen.sh
#
# **Warum das nötig ist.** Im Arbeitsstand sind die Namen längst
# ersetzt, aber in zwei alten Commit-Nachrichten stehen sie noch – und
# eine davon ist ausgerechnet die Nachricht, die das Ersetzen
# ankündigt. In einem öffentlichen Repository ist die Historie genauso
# lesbar wie der aktuelle Stand.
#
# **Was danach anders ist.** Sämtliche Commit-Kennungen ändern sich.
# Das ist bei diesem Repository unkritisch, weil niemand sonst daran
# arbeitet – aber es verlangt einen erzwungenen Push, und
# `git filter-repo` entfernt vorher den Verweis auf GitHub. Beides
# erledigt dieses Skript.
#
# Vorher wird eine Sicherung angelegt. Wenn etwas schiefgeht:
#     rm -rf .git && mv .git-sicherung .git

set -euo pipefail
cd "$(dirname "$0")/.."

if [ -d .git-sicherung ]; then
    echo "Es gibt bereits .git-sicherung – bitte erst prüfen und wegräumen."
    exit 1
fi

echo "Sicherung anlegen …"
cp -r .git .git-sicherung

ersetzungen="$(mktemp)"
trap 'rm -f "$ersetzungen"' EXIT
cat > "$ersetzungen" <<'MUSTER'
In Tests und Kommentaren standen==>In Tests und Kommentaren standen
zwei echte Albumnamen aus dem Bestand, an dem entwickelt wurde. Sie==>zwei echte Albumnamen aus dem Bestand, an dem entwickelt wurde. Sie
Nordsee 2023==>Nordsee 2023
Nordsee==>Nordsee
Mein Viertel==>Mein Viertel
MUSTER

echo "Historie umschreiben …"
git filter-repo --replace-message "$ersetzungen" --replace-text "$ersetzungen" --force

echo "Verweis auf GitHub wiederherstellen …"
git remote add origin https://github.com/Stephan-Lefty/WOLKENErnte.git

echo
echo "Prüfung – hier darf nichts mehr stehen:"
git log --all --format="%s%n%b" | grep -niE "Nordsee|Mein Viertel" || echo "  nichts gefunden, sauber."

echo
echo "Jetzt erzwungen hochladen:"
echo "    git push --force origin main"
echo
echo "Danach kann .git-sicherung weg:"
echo "    rm -rf .git-sicherung"
