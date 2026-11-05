#!/usr/bin/env bash
# Odtwarza przykładowe eksporty z SYNTETYCZNYCH stron testowych (tests/fixtures).
# To NIE są aktualne oferty z Allegro — przebiegi są oznaczone jako testowe (--testowe).
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
PY=${PYTHON:-python}
$PY -m allegro_ceny --katalog-danych "$TMP" importuj --profil profile/stihl_ms391.toml --testowe \
    tests/fixtures/strona_1.html tests/fixtures/strona_2.html tests/fixtures/import_przyklad.csv > /dev/null
$PY -m allegro_ceny --katalog-danych "$TMP" importuj --profil profile/stihl_ms391.toml --testowe \
    tests/fixtures/strona_1_pozniej.html tests/fixtures/strona_2.html > /dev/null
$PY -m allegro_ceny --katalog-danych "$TMP" analiza --profil profile/stihl_ms391.toml > przyklady/TESTOWE_analiza.txt
$PY -m allegro_ceny --katalog-danych "$TMP" historia --profil profile/stihl_ms391.toml > przyklady/TESTOWE_historia.txt
$PY -m allegro_ceny --katalog-danych "$TMP" eksport --profil profile/stihl_ms391.toml --katalog "$TMP/eksport" > /dev/null
cp "$TMP/eksport/stihl_ms391_przebieg2.csv" przyklady/TESTOWE_stihl_ms391.csv
cp "$TMP/eksport/stihl_ms391_przebieg2.json" przyklady/TESTOWE_stihl_ms391.json
cp "$TMP/eksport/stihl_ms391_przebieg2_ai.json" przyklady/TESTOWE_stihl_ms391_ai.json
rm -rf "$TMP"
echo "Gotowe: przyklady/TESTOWE_*"
