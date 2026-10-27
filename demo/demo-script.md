# Offline backend rehearsal and frontend handoff

Audric's automated integration path runs without public network access:

```powershell
.\.venv\Scripts\python.exe -I -m sentriflow.verification --output docs/evidence/kpis.json
```

It starts a temporary destination server, HTTPS certificates, proxy, API and WebSocket client;
rehearses tracker Halt → PII Allow/Block → score update three times; tests all seeded PII
encodings, persistent rules and timeout Block; and writes measured aggregate results.
It changes neither the Windows proxy nor the system certificate store.

For the eventual dashboard recording, install/setup the backend, run `sentriflow seed-demo`
while stopped, start SentriFlow, and start `python demo/test-server/server.py` separately.
Open the dashboard using the launch token printed by the backend (or the Vite URL with the
same fragment). The R4 traffic/rules/Halt pages must be connected before this click path:

1. Show the live traffic page and explain that inspection stays on this device.
2. In another terminal run the explicit-proxy curl command from `docs/windows-setup.md`.
3. Show the pending Halt with dummy name/email/card labels and redacted samples.
4. Choose Block once. The curl request receives 403 and the receiver sees no payload.
5. Send again; choose Allow once. The receiver returns its fixed acknowledgement.
6. Send again; choose Always block. Repeat and show the saved rule blocking immediately.
7. Show alerts, the transparent score breakdown and the saved rule. Delete the rule.
8. Send again without answering; show timeout Block. Confirm masked history only.
9. Record actual Windows attribution and decision timing using `docs/testing.md`.
10. Stop monitoring, restore routing and remove CA trust before ending the recording.

The synthetic tracker seed `tracker.demo.test` is reserved test data and is not a public
blocklist. The automated verifier uses `localhost` as a synthetic tracker destination.
Production blocklist ingestion remains R3's task. Do not present those fixtures as real
threat intelligence or the automated run as a completed dashboard demonstration.
