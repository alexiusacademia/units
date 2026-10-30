#!/bin/sh
# units' UI tests: drives the example app (examples/main.tsl) without a
# window, typing values and units and picking systems, and checks what it
# shows afterwards.
# Run from anywhere: sh tests/ui.sh
#
# Author: Alexius Academia
# Date: 2026-10-30

cd "$(dirname "$0")/.." || exit 1
TESSEL="${TESSEL:-tessel}"
failed=0
passed=0

# check NAME SCRIPT EXPECTED... : every EXPECTED text must be in the output.
check() {
    name="$1"
    script="$2"
    shift 2
    out=$(TESSEL_SCRIPT="$script" "$TESSEL" run examples 2>&1)
    for want in "$@"; do
        if printf '%s\n' "$out" | grep -qF -- "$want"; then
            :
        else
            echo "FAIL  $name: no \"$want\""
            printf '%s\n' "$out" | grep -E 'TextField|Text "|^script|error' | head -12 | sed 's/^/        /'
            failed=$((failed + 1))
            return
        fi
    done
    echo "ok    $name"
    passed=$((passed + 1))
}

nl='
'
# Types into the value field (1) or the unit field (2), replacing its text.
value() { printf 'click field 1\nkey cmd+a\ntype %s\n' "$1"; }
unit() { printf 'click field 2\nkey cmd+a\ntype %s\n' "$1"; }

check "starts with 5' 6 1/4\"" "tree" 'Text "length · 1.68275 m in SI base units"' \
    'Text "66.25"' 'Text "1682.75 mm"' 'Text "5'"'"' 6 1/4\""'
check "a unit weight" "$(value '120 pcf')${nl}tree" 'Text "unit weight' 'Text "18.8505"' 'Text "kN/m³"'
check "in the US system" "$(value '120 pcf')${nl}click \"US\"${nl}tree" 'Text "120 pcf"'
check "in SI kN-m" "$(value '120 pcf')${nl}click \"SI kN-m\"${nl}tree" 'Text "18.8505 kN/m³"'
check "into a unit typed" "$(value '120 pcf')${nl}$(unit 'kN/m^3')${nl}tree" 'Text "18.850496 kN/m³"'
check "a wrong unit says why" "$(value '120 pcf')${nl}tree" 'mm is a length, not a unit weight'
check "a temperature" "$(value '68 °F')${nl}$(unit '°C')${nl}tree" 'Text "temperature' 'Text "20 °C"'
check "a sum of loads" "$(value '3 kN/m + 200 lbf/ft')${nl}tree" 'Text "force per length' 'Text "5.91878 kN/m"'
check "a sum of lengths" "$(value '1 m + 50 mm')${nl}$(unit 'in')${nl}tree" 'Text "41.338583 in"'
check "a moment in kip-ft" "$(value '100 kN·m')${nl}click \"US kip-ft\"${nl}tree" 'Text "73.7562 kip·ft"'
check "a level in dBm" "$(value '10 dBm')${nl}$(unit 'mW')${nl}tree" 'Text "10 mW"'
check "an unknown unit" "$(value '3 frobs')${nl}tree" 'Text "\"frobs\" isn'"'"'t a unit"'
check "feet and inches from metres" "$(value '2 m')${nl}tree" 'Text "6'"'"' 6 3/4\""'
check "a flow in cfs" "$(value '1 MGD')${nl}click \"US\"${nl}tree" 'Text "1.54723 cfs"'
check "dark" "appearance dark${nl}tree" 'Text "length · 1.68275 m in SI base units"'

echo "$passed passed, $failed failed"
[ "$failed" -eq 0 ]
