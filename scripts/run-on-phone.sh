#!/usr/bin/env bash
#
# Build, install and launch SevakAI on a physical Android phone over USB.
#
#   bash scripts/run-on-phone.sh
#
# Sets up `adb reverse` so the phone reaches the laptop's backend at
# 127.0.0.1:8010 without either device needing to be on the same Wi-Fi.
#
set -uo pipefail

# adb takes device-side paths; Git Bash would otherwise rewrite them into
# Windows paths and produce baffling errors.
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT=8010
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"

# --- Locate the tools ------------------------------------------------------
ADB="${ADB:-}"
if [ -z "$ADB" ]; then
  for candidate in \
    "$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe" \
    "$HOME/AppData/Local/Android/Sdk/platform-tools/adb.exe" \
    "$HOME/Library/Android/sdk/platform-tools/adb" \
    "$HOME/Android/Sdk/platform-tools/adb" \
    "$(command -v adb 2>/dev/null)"
  do
    [ -n "${candidate:-}" ] && [ -x "$candidate" ] && ADB="$candidate" && break
  done
fi
if [ -z "$ADB" ]; then
  echo "Could not find adb. Set ADB=/path/to/adb and re-run." >&2
  exit 1
fi

if [ -z "${JAVA_HOME:-}" ]; then
  for candidate in \
    "/c/Program Files/Eclipse Adoptium/jdk-21.0.12.101-hotspot" \
    "/c/Program Files/Eclipse Adoptium"/jdk-*
  do
    [ -x "$candidate/bin/java.exe" ] && export JAVA_HOME="$candidate" && break
  done
fi

step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32mok\033[0m   %s\n' "$*"; }
warn() { printf '  \033[33mwarn\033[0m %s\n' "$*"; }
die()  { printf '  \033[31mfail\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. Device -------------------------------------------------------------
step "1. Looking for a connected phone"
DEVICES="$("$ADB" devices | awk 'NR>1 && $2=="device" {print $1}')"
UNAUTH="$("$ADB" devices | awk 'NR>1 && $2=="unauthorized" {print $1}')"

if [ -n "$UNAUTH" ]; then
  die "Phone is connected but not authorised. Unlock it and accept the
       'Allow USB debugging?' prompt, then re-run."
fi
if [ -z "$DEVICES" ]; then
  die "No device found. Check that:
       - the phone is plugged in with a data cable (not charge-only),
       - Developer options are on (tap Build number 7 times in Settings > About),
       - USB debugging is enabled,
       - you accepted the authorisation prompt on the phone."
fi
for device in $DEVICES; do
  MODEL="$("$ADB" -s "$device" shell getprop ro.product.model 2>/dev/null | tr -d '\r')"
  SDK="$("$ADB" -s "$device" shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r')"
  ok "$device — $MODEL (API $SDK)"
  if [ -n "$SDK" ] && [ "$SDK" -lt 26 ] 2>/dev/null; then
    die "This app needs Android 8.0 (API 26) or newer."
  fi
done
DEVICE_COUNT="$(printf '%s\n' $DEVICES | wc -l | tr -d ' ')"
if [ "$DEVICE_COUNT" -gt 1 ]; then
  warn "More than one device attached; using the first. Unplug the others, or
       set ANDROID_SERIAL to choose."
fi

# --- 2. Backend ------------------------------------------------------------
step "2. Checking the backend"
HEALTH="$(curl -s --max-time 5 "http://127.0.0.1:$PORT/api/health" 2>/dev/null || true)"
if [ -z "$HEALTH" ]; then
  die "Nothing answering on 127.0.0.1:$PORT. Start it with:
       cd backend && ./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port $PORT"
fi
ok "backend is up"
case "$HEALTH" in
  *'"llm_ready":true'*) ok "LLM configured" ;;
  *) warn "LLM is NOT configured — visits will be classified by rules only.
       Add GROQ_API_KEY to backend/.env." ;;
esac
case "$HEALTH" in
  *'"guideline_chunks":0'*) warn "No guideline corpus indexed. Run:
       cd backend && python -m scripts.fetch_guidelines && python -m app.rag.ingest --reset" ;;
  *) ok "guideline corpus indexed" ;;
esac

# --- 3. Port forwarding ----------------------------------------------------
step "3. Forwarding port $PORT to the phone"
# `adb reverse` makes the PHONE's 127.0.0.1:PORT reach the LAPTOP's port.
# Note this is not 10.0.2.2 — that address is emulator-only.
"$ADB" reverse --remove-all >/dev/null 2>&1 || true
if "$ADB" reverse "tcp:$PORT" "tcp:$PORT" >/dev/null 2>&1; then
  ok "phone can now reach the backend at 127.0.0.1:$PORT"
else
  die "adb reverse failed. Some devices need USB mode set to 'File transfer'."
fi

# --- 4. Build and install --------------------------------------------------
step "4. Building the app"
( cd "$ROOT/android" && ./gradlew :app:assembleDebug --console=plain -q ) \
  || die "Build failed. Run ./gradlew :app:assembleDebug in android/ to see why."
[ -f "$APK" ] || die "APK not found at $APK"
ok "built $(du -h "$APK" | cut -f1 | tr -d ' ')"

step "5. Installing"
INSTALL="$("$ADB" install -r "$APK" 2>&1)"
case "$INSTALL" in
  *Success*) ok "installed" ;;
  *INSTALL_FAILED_UPDATE_INCOMPATIBLE*)
    warn "A different build is installed; removing it first"
    "$ADB" uninstall in.sevakai.app >/dev/null 2>&1
    "$ADB" install -r "$APK" >/dev/null 2>&1 && ok "installed" || die "$INSTALL" ;;
  *) die "$INSTALL" ;;
esac

# --- 6. Launch -------------------------------------------------------------
step "6. Launching"
"$ADB" shell am start -n in.sevakai.app/.MainActivity >/dev/null 2>&1 \
  && ok "launched" || die "Could not start the app"

cat <<EOF

Done. On the phone:

  1. On the sign-in screen, tap "Server" at the bottom.
  2. Choose the "USB cable" preset (127.0.0.1:8010).
  3. Tap "Test connection" — it should report the patient count.
  4. Sign in with 9000000002 / PIN 1234.

If you unplug the phone, run this again (or just \`adb reverse tcp:$PORT tcp:$PORT\`)
— the forward does not survive a disconnect.

To use Wi-Fi instead of USB, put your laptop's IP in the Server screen and make
sure the backend was started with --host 0.0.0.0.

Logs:  $ADB logcat -s SevakRepo:* SevakSpeech:* SevakSync:* AndroidRuntime:E
EOF
