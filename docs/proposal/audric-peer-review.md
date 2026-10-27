# P14 — Audric Yusuf Maynard Simatupang's peer review

Review date: **27 October 2026 (Asia/Jakarta)**. Input: the supplied
*Preliminary Project Document: Project SentriFlow*, preliminary proposal v1.0.
The repository's `FPH_Senklok.md` is empty and an assembled full proposal was not supplied.
This is a completed preliminary review; final-draft P14 acceptance is still pending P13.

Scores below are an internal assessment using the five weights stated in the tracker, not
an organizer's grade. The official guideline was not supplied, so its formatting or scoring
requirements cannot be independently certified from this material.

| Criterion | Score | Evidence in preliminary PDF | Highest-value revision |
| --- | ---: | --- | --- |
| Problem and user validation | 8 / 20 | Sections 2–3 clearly state visibility, destination and payload gaps, but provide no survey/interview results or sourced scale estimates | Add R1's genuine validation counts, method, representative findings and sources; distinguish unmet needs from assumptions |
| Proposed solution | 21 / 25 | Sections 4–5 and 7 connect local interception, configurable patterns, Halt and persistence with a coherent user workflow | Add a verified existing-tools comparison and an explicit differentiation claim; show the actual four decision choices |
| Technical implementation | 17 / 25 | Sections 6–10 explain token/Origin controls, SQLite, source-port attribution and CA risk | Replace the flattened architecture figure, add ERD/API diagrams, choose Windows 11, and cite actual prototype evidence with its scope |
| Impact and sustainability | 7 / 15 | Privacy benefits and a post-hackathon roadmap are described qualitatively | Define observable user outcomes, maintenance responsibility and blocklist/GeoIP licensing/update process; avoid invented impact statistics |
| Development plan | 9 / 15 | Sections 11–15 include risks and phased work, but owners/dates are placeholders and the hour-based plan conflicts with the tracker | Use named tracker owners and actual dependencies; separate completed work, pending evidence and stretch scope |
| **Total** | **62 / 100** | Preliminary-document readiness only | Re-score the assembled full draft after P13 |

Prioritized fixes for the assembled proposal:

1. **R1: replace assumptions with user evidence.** Document recruitment, sample size,
   questions, response counts and interview notes. If validation is incomplete, say so;
   do not fill counts, percentages or participant quotations from estimates.
2. **R4 with R2/R3: rebuild five legible system-design figures.** The supplied PDF's
   page 4 was visually inspected: the architecture is rendered as a black label strip
   followed by near-white component names on white, without legible connections. Replace
   it with clear architecture, Halt workflow, use case, ERD and API figures using actual
   code names and the frozen API contract. The preliminary PDF has nine pages; that does
   not establish the final assembled proposal's page count.
3. **R1: resolve platform and schedule placeholders.** Select Windows 11 as already decided
   in the repository. The tracker assigns Audric to proxy/backend/Halt/integration; the
   generic build-plan role numbers differ. Use names rather than copying those numbers.
   Record actual dates; the 20–26 October window has elapsed as of this review.
4. **R2/R3: integrate qualified prototype results.** The local backend report measures
   28/28 named loopback flows, 18/18 seeded PII matches, three successful backend rehearsals,
   and decision timing. It does not establish 10-minute Windows browser attribution,
   native CA trust, crash recovery, UI readiness or a 30-minute stability session.
5. **R3: substantiate feasibility and limits.** Explain system-proxy coverage, QUIC bypass,
   Firefox trust, possible TLS pinning, bounded inspection and offline GeoIP requirements.
   The runtime reports failed TLS as encrypted/not inspected, without proving pinning.
6. **R1/R3: add verified references and a tool comparison.** The preliminary PDF has no
   bibliography. Cite official documentation for tool features, licenses and technical
   claims before finalizing the IEEE reference order. No new market/legal claims were
   introduced in this review.
7. **R4: assemble and inspect the actual submission artifact.** Confirm the tracker-stated
   15-page limit against the official guideline, replace the trailing stray list marker,
   remove placeholders, check figure legibility/fonts/links, and export `FPH_Senklok.pdf`.
   No submission, font, page-count or PDF-format check is claimed by this source review.

R2 handoff inputs now available: [architecture](../architecture.md), [API contract](../api.md),
[test methodology](../testing.md), [measured backend evidence](../evidence/kpis.json), and
[implementation worklog](../audric-worklog.md). Screenshots and a recording must come from
the actual final dashboard/Windows session. Re-run this rubric review on the full assembled
proposal and list remaining fixes before R1 submits it.
