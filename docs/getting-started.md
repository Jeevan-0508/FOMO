# Getting started

FOMO is a static freight and supply-chain risk signal monitor. It presents the project's current signal classifications and supporting context as a browsable dashboard; it is not a live carrier feed or an automated fraud verdict.

## Try it

Open the [live dashboard](https://jeevan-0508.github.io/FOMO/). Start with the signal overview, then inspect the supporting notes and reliability section before treating a signal as an investigation lead.

## Run locally

```bash
python3 build_dashboard.py
python3 -m http.server 4173
```

Open <http://localhost:4173/>. Run the repository's inspector against the deployed or local URL when reviewing a release.

## Reliability boundary

Signal labels are decision-support presentation. They require context and human review; they do not establish that a carrier, lane or incident is fraudulent.
