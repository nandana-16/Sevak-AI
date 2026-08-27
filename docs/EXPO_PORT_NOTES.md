# Porting the worker app to React Native (Expo)

The web app in `web/worker-app/` is a fast reference implementation. When Android
tooling (Node ✅ already installed on this machine, plus Java + Android Studio/SDK or a
physical device with Expo Go) is ready, porting to Expo is a frontend-only exercise —
the backend contract does not change. Suggested mapping:

| Web app piece | Expo equivalent |
|---|---|
| `src/api.js` (axios + JWT interceptor) | Same file works almost as-is in React Native |
| `src/offline.js` (IndexedDB queue) | `expo-sqlite` table with the same `localId/record_type/record_json` shape |
| Browser `SpeechRecognition` in `RecordVisit.jsx` | `expo-av` to record audio, then either upload `audio_base64` to `/api/v1/visits/voice` (server-side Bhashini) or an on-device STT library |
| `navigator.onLine` / online-offline events | `@react-native-community/netinfo` |
| CSS in `index.css` | React Native `StyleSheet` — the color tokens (`--primary`, risk badge colors) translate directly |
| React Router-less screen-state switching in `App.jsx` | Same pattern works in RN, or swap in `@react-navigation/native` |

To start:

```bash
npx create-expo-app worker-app-native
cd worker-app-native
npx expo install expo-av expo-sqlite @react-native-community/netinfo
```

Then port screen-by-screen from `web/worker-app/src/components/`, reusing `api.js`'s
function signatures unchanged (same endpoints, same JWT header, same request/response
shapes) — only the recording/storage APIs are RN-specific.
