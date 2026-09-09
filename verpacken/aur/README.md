# WOLKENErnte im AUR

Damit `pamac update` WOLKENErnte mit dem Rest des Systems mitzieht.

**Warum es zwei PKGBUILDs gibt.** [`../arch/PKGBUILD`](../arch/PKGBUILD)
baut, was gerade im Arbeitsverzeichnis liegt – zum Ausprobieren während
der Entwicklung. Dieses hier baut aus dem **veröffentlichten
Quellarchiv**, mit Prüfsumme. Ein AUR-Paket, das auf einen Ordner auf
einer fremden Platte zeigt, ließe sich nirgends bauen.

## Einmalig einrichten

Das AUR spricht ausschließlich über SSH. Einen Schlüssel anlegen, falls
noch keiner da ist:

```
ssh-keygen -t ed25519 -f ~/.ssh/aur -C "AUR"
cat ~/.ssh/aur.pub
```

Den öffentlichen Teil unter <https://aur.archlinux.org/account/> im
Feld »SSH Public Key« eintragen. Dann `~/.ssh/config` ergänzen:

```
Host aur.archlinux.org
    User aur
    IdentityFile ~/.ssh/aur
```

Prüfen, ob es geht – die Antwort lautet »Interactive shell is
disabled«, und das ist die richtige:

```
ssh aur.archlinux.org
```

Das noch leere Paket-Repository holen:

```
mkdir -p ~/aur && cd ~/aur
git clone ssh://aur@aur.archlinux.org/wolkenernte.git
```

**Der Name ist danach belegt.** Er lässt sich nicht mehr ändern und
nicht ohne Weiteres löschen; wer ein Paket aufgibt, gibt es an das AUR
zurück, damit ein anderer es übernehmen kann.

## Das erste Mal hochladen

```
cd "/mnt/raid/eigene Daten/GitHub/Stephan-Lefty/WOLKENErnte/verpacken/aur"
makepkg -f                                  # baut es wirklich?
cp PKGBUILD .SRCINFO ~/aur/wolkenernte/
cd ~/aur/wolkenernte
git add PKGBUILD .SRCINFO
git commit -m "wolkenernte 0.4.1"
git push
```

`.SRCINFO` **muss** mit. Das AUR liest ausschließlich diese Datei; ein
neues PKGBUILD mit alter `.SRCINFO` daneben ergibt ein Paket, das im
AUR weiterhin die alte Fassung anbietet – ohne dass irgendwo etwas
fehlschlägt.

## Bei jeder neuen Fassung

Erst den Release auf GitHub anlegen, dann:

```
python3 verpacken/aur/nachziehen.py
```

Das holt das Quellarchiv, rechnet die Prüfsumme daraus, trägt beides
ein, setzt `pkgrel` zurück und erzeugt `.SRCINFO` neu. Danach die
Befehle von oben, mit der neuen Nummer in der Commit-Zeile.

**Warum das Skript und nicht drei Handgriffe:** Beim Nachziehen von
Hand vergisst man genau eine Sache – die Prüfsumme. Das Paket baut dann
trotzdem, aus dem alten zwischengespeicherten Archiv, und es fällt erst
auf, wenn ein fremder Rechner es zum ersten Mal wirklich lädt.

## Was Nutzer danach tun

```
pamac install wolkenernte
```

oder mit yay:

```
yay -S wolkenernte
```

Und von da an kommt es mit jeder Systemaktualisierung mit.
