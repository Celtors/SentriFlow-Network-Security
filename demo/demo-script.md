# Offline demonstration

1. Run `scripts/build.ps1` then `scripts/run.ps1`. Open http://127.0.0.1:8787, enter the terminal token, and keep the dashboard direct.
2. Start `python demo/test-server/server.py` in another terminal.
3. Through explicit proxy 127.0.0.1:8080, POST the seeded dummy email/phone/card to http://127.0.0.1:9090/submit. Exact curl command: [Windows setup](../docs/windows-setup.md).
4. Show the masked Halt prompt. Block and confirm local 403. Repeat, Allow once, and confirm origin 200. Repeat without answering to demonstrate default Block after 30 seconds.
5. Remember a decision, review its exact process+host scope in Rules, edit/delete it. Show the alert list and disclosed score formula. Never claim that a pattern proves malicious behavior.
6. GET http://127.0.0.1:9090/stream through the proxy. It sends chunks slowly; the speed chart should update before the response completes.
7. Demonstrate the reserved tracker.sentriflow.test request and block it. It has no real reachable origin; Allow is not a successful tracker-site demo.
8. Finish by restoring any explicitly enabled routing and removing any explicitly installed CA trust.

The optional automated Edge script repeats actual decisions and saves screenshots/measurements. A recorded backup video and representative browsing KPI session still need to be prepared.
