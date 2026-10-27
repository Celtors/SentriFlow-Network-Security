# Existing Solutions and Opportunity (task P06)

Draft for the "Problem Analysis: existing solutions and opportunity" section of the Full Proposal (FPH_Senklok).
Evidence cut-off: official product pages read on **27 Oct 2026**.

**Method.** Only official sources (product site, official repository or official documentation) were used [1]-[9].
A capability is marked **Yes** only when the source states it. **Not documented** means the official page does
not mention it. This is *not* proof that the capability is missing, and the text below never claims it is.

## 1. Comparison

| Tool | Platform | Licence / price | What it does (as documented) | Limit relevant to our problem |
| --- | --- | --- | --- | --- |
| **GlassWire** [1] | Windows, Android | Free download, paid premium upgrade; open source not stated | Network usage "broken down by IP/Host, app, network traffic types"; "Ask to connect" mode to allow or deny new app connections; alert when a new app accesses the network; history of past connections | Works on apps and destinations. Inspection of request content is not documented |
| **Little Snitch** [2] | macOS (page names macOS only) | Free download, runs in demo mode without a licence key (Network Monitor expires after 30 days) | Alert whenever an app wants to connect; allow or block with one click; Network Monitor; blocklists; traffic volumes, servers, ports, protocols | Not available on Windows. Request content is not documented |
| **Wireshark** [3], [4] | Windows, macOS, Linux | Free, open source (GPL v2) | "Deep inspection of hundreds of protocols"; capture and browse network traffic | TLS decryption needs secrets exported from the client application (key log file, `SSLKEYLOGFILE`) or a private key in limited cases [4]. Blocking or asking the user is not documented |
| **mitmproxy** [5], [6] | Windows, Linux, Docker (macOS via Homebrew) | Free, open source (MIT) | Intercept, inspect, modify and replay HTTP/1, HTTP/2, HTTP/3, WebSockets and TLS-protected traffic; Python scripting API; **Local Capture on Windows, Linux and macOS, targeted by process name or PID** [6] | A developer tool. User consent prompts and personal-data detection are not documented |
| **OpenSnitch** [7] | GNU/Linux (Windows not mentioned) | Free, open source (GPL-3.0) | "Interactive outbound connections filtering"; block ads, trackers or malware domains system wide; configure the system firewall (nftables) from the GUI | Linux only. Request content is not documented |
| **Portmaster** [8], [9] | Windows, Linux | Free, open source (GPL-3.0); some features paid | Per-app settings; secure DNS; automatic tracker and malware blocklists; monitor all network activity; packets intercepted at raw packet level (Windows kernel driver); "Allow Domain" / "Allow IP" exceptions; desktop prompt notifications | Rules are described in terms of domains, IPs and applications. HTTPS decryption and request content inspection are not documented; per-app bandwidth and activity history are marked as paid |

## 2. Capability matrix (documented in the official source)

| Capability | GlassWire | Little Snitch | Wireshark | mitmproxy | OpenSnitch | Portmaster |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| Runs on Windows | Yes | No | Yes | Yes | Not mentioned | Yes |
| Attributes traffic to an application | Yes | Yes | Not documented | Yes (Local Capture) | Yes (application firewall) | Yes |
| Asks the user to allow or deny a connection | Yes | Yes | Not documented | Not documented | Yes | Partly (prompt notifications) |
| Sees decrypted request content | Not documented | Not documented | Only with exported TLS secrets | Yes | Not documented | Not documented |
| Detects personal data in outgoing requests | Not documented | Not documented | Not documented | Not documented | Not documented | Not documented |
| Pauses one request after inspecting its content, until the user decides | Not documented | Not documented | Not documented | Not documented | Not documented | Not documented |
| Free and open source | Free, source not stated | Not stated | Yes | Yes | Yes | Yes (some paid) |

## 3. Reading the table

- **Connection-level tools** (GlassWire, Little Snitch, OpenSnitch, Portmaster) answer *"which app talks to which
  destination"* and let the user allow or block it. Their official pages describe decisions based on
  applications, domains, IPs and ports.
- **Content-level tools** (Wireshark, mitmproxy) can show *what is inside* a request, but are built for
  developers and analysts. mitmproxy can already target a single process on Windows [6], so attribution alone
  is not our contribution; neither tool documents a consent flow or personal-data detection.
- **No source in this review documents detection of personal data inside outgoing requests**, and none documents
  pausing an individual request based on its inspected content. (Connection-level tools do ask before a new
  connection is allowed; that is a decision about the app and destination, not about what the request carries.)

## 4. Opportunity statement (paste-ready)

> Existing tools stop at one of two points. Application firewalls such as GlassWire, Little Snitch, OpenSnitch and
> Portmaster let users allow or block connections per application, but their official documentation describes
> decisions based on applications, destinations and ports, not on what the request carries. Interception tools such
> as mitmproxy and Wireshark can reveal request content, yet they are developer tools without a consent step.
> The opportunity is a **local Windows tool for ordinary users** that attributes each outgoing request to its
> application, inspects the user's own decrypted traffic for personal data, **holds the request** and asks the user
> in plain language, and **blocks by default** when nobody answers. SentriFlow builds on mitmproxy's proven
> interception engine and adds the missing consent and personal-data layer, with all data kept on the device.

## 5. Before submitting (checklist for the author)

- [ ] Re-open each source in the reference list; product pages change. Update the date if anything is edited.
- [ ] "Not documented" cells are the weakest part of the argument. If any is contradicted by a deeper page
      (for example Portmaster's technical documentation on HTTPS), correct the matrix and the opportunity statement.
- [ ] Add the survey/interview evidence from P02 to Section 4 (task P11), for example how many respondents want to
      approve data leaving their device.
- [ ] Confirm GlassWire's premium price and Little Snitch's price on their pricing pages if the proposal quotes costs.
- [ ] Keep this section within the page budget; the matrix in Section 2 can replace the long table if space is short.

## References (IEEE style, in order of first appearance)

[1] GlassWire, "GlassWire: network monitor and firewall," glasswire.com. [Online]. Available: https://www.glasswire.com/ (accessed Oct. 27, 2026).

[2] Objective Development, "Little Snitch: network monitor and application firewall for macOS," obdev.at. [Online]. Available: https://obdev.at/products/littlesnitch/index.html (accessed Oct. 27, 2026).

[3] Wireshark Foundation, "Wireshark: go deep," wireshark.org. [Online]. Available: https://www.wireshark.org/ (accessed Oct. 27, 2026).

[4] Wireshark Foundation, "TLS," Wireshark Wiki. [Online]. Available: https://wiki.wireshark.org/TLS (accessed Oct. 27, 2026).

[5] mitmproxy Project, "mitmproxy: a free and open source interactive HTTPS proxy," mitmproxy.org. [Online]. Available: https://mitmproxy.org/ (accessed Oct. 27, 2026).

[6] mitmproxy Project, "Proxy modes," mitmproxy docs. [Online]. Available: https://docs.mitmproxy.org/stable/concepts/modes/ (accessed Oct. 27, 2026).

[7] evilsocket et al., "OpenSnitch: GNU/Linux interactive application firewall," GitHub. [Online]. Available: https://github.com/evilsocket/opensnitch (accessed Oct. 27, 2026).

[8] Safing, "Portmaster: a free and open-source application firewall," GitHub. [Online]. Available: https://github.com/safing/portmaster (accessed Oct. 27, 2026).

[9] Safing, "Frequently asked questions," Portmaster Docs. [Online]. Available: https://docs.safing.io/portmaster/faq (accessed Oct. 27, 2026).
