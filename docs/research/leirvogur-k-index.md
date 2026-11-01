# Numerical Leirvogur local K-index data

Researched on 2026-11-01. The feature design selects this numerical source and a ten-minute polling interval; the access/semantics limitations below remain documented.

## Recommended candidate

Use the public [Leirvogur numerical text file](https://flux.phys.uit.no/Kindice/k_lrv1a.txt), linked as “The Numbers” under Leirvogur on [TGO's K-index page](https://flux.phys.uit.no/Kindice/). Prefer that numerical product to reading chart pixels or calculating K from raw magnetic measurements. The station identifier is LRV. A documented JSON API has not been verified.

This recommendation is an engineering inference from the directly linked numerical product, not a provider statement that this is a supported API or a grant of reuse rights.

The same live source page embeds the [Leirvogur K-index graph](https://flux.phys.uit.no/Kindice/k_lrv1a.gif). Link this graph in `/kindex nuna` replies as requested; obtain numeric values from the TXT file rather than the graph.

## Live sample and format

A direct HTTPS fetch on 2026-11-01 at approximately 21:36 UTC returned HTTP 200 and:

```text
K-Indices for Leirvogur

26 oct. 2026 1002 2211
27 oct. 2026 2211 2131
28 oct. 2026 3111 1223
29 oct. 2026 3401 1000
30 oct. 2026 0011 1236
31 oct. 2026 5543 3476
01 nov. 2026 7543 233x
```

Observed response metadata:

- `Content-Type: text/plain; charset=UTF-8`
- `Last-Modified: Sun, 01 Nov 2026 21:09:01 GMT`
- `ETag: "ba-65f3d704477dd"`

There are seven dated rows with eight single-character slots grouped four plus four. These are individual K values, not two multi-digit measurements. Dates use English month abbreviations. The file has no embedded generation timestamp or schema version. HTTP metadata describes the file, not an observation's interval or age.

Web-search snapshots returned an older October sample; they cannot establish the freshness of this live endpoint. Source clients and freshness checks must use direct responses rather than search-index dates.

## Time and scientific meaning

[TGO's method description](https://flux.phys.uit.no/SSASWE/info/knuminfo.html) describes integer 0–9 local K values from one-minute horizontal-field measurements, with daily variation removed. It calculates the preceding three-hour range at fixed UT boundaries, yielding eight intervals per day: 00–03 through 21–24. It labels the procedure provisional because it differs slightly from the IAGA procedure. This older explanation lists other stations, not LRV; an LRV-specific confirmation of identical timing and calculation has not been located.

Under that interval interpretation, the sampled row's last numeric slot is K=3 for 18:00–21:00 UTC, and its `x` occupies 21:00–24:00. That matches the sample's time of day, but does not prove the meaning of all future or missing markers. Treat `x` as unavailable, never zero; exact sentinel semantics remain undocumented in the material inspected.

There is no verified evidence here of an instantaneous or in-progress LRV K estimate. Proposed wording is “latest available provisional local K at Leirvogur,” with its interval and freshness shown. Availability nine minutes after an interval boundary in one sample is an observation, not a publication-latency guarantee.

The [official live map](https://flux.phys.uit.no/Kindice/kindex-mapview.html) uses the same LRV text file. Its JavaScript selects a numeric digit before `x`/`X` for the displayed value and accepts those markers as missing slots in its daily parser. Its display refresh is every 30 minutes, which is not evidence of the source's generation cadence. Read the HTTPS file directly; the map's third-party browser proxy is unnecessary for the bot. Parse whole dated rows rather than copying the map's loose digit-selection fallback.

The [planetary Kp index](https://www.spaceweather.gov/products/planetary-k-index) combines station observations and is a different product. Missing Leirvogur data must not silently become Kp data, and local K alerts should not be labelled as NOAA planetary G-scale storm levels.

## Access and attribution

[TGO's May 2025 data-access notice](https://flux.phys.uit.no/div/DataAccess.html) preserves originating institutions' rights, expects acknowledgement, requires institution-specific agreements for commercial use, and says it has stopped provisioning real-time magnetometer data for app/service/product development. The notice discusses raw/digital access and passwords; its applicability to the openly linked derived K-index file is unclear. Public accessibility alone does not establish an open licence. Attribute the source and avoid claiming that the repository's MIT licence covers provider data.

This is an unresolved access question to record, not proof that the public K file is forbidden for this bot. No provider has been contacted or permission represented as granted.

## Alternatives investigated

- The University of Iceland's [English](http://cygnus.rhi.hi.is/~halo/lrv.html) and [Icelandic](http://cygnus.rhi.hi.is/~halo/leirvogur.html) observatory pages were reachable over HTTP while HTTPS connections failed during research. They publish magnetic component graphs, described as updating every ten minutes, and historical graph links. A numerical local-K endpoint was not found there. The graph cadence must not be treated as the K-index publication cadence.
- The [Icelandic Met Office's explanation](https://www.vedur.is/vedur/frodleikur/greinar/nr/2545) links the University's observatory page and identifies the University as operator. Its separate GFZ Kp display is planetary, not an alternative measurement of LRV local K.
- TGO's archive form leads to dated station images through `knum.cgi`; it did not reveal a better numerical product.

The public TGO TXT remains the best verified numerical candidate. No documented current-bin LRV estimate or better numerical API was found; this is a research result, not proof that none exists.

## Implementation implications

- Parse the station header, whole dates, exactly eight slots per row, and only supported K values or known missing markers. A format change must produce unavailable data, not fabricated observations.
- Record interval start/end separately from fetch time and HTTP Last-Modified.
- Poll every 10 minutes, with timeout/backoff and conditional requests where supported. A three-hour product does not warrant second-by-second polling.
- Distinguish no data, stale data and provider failure; stale values may be useful for display with their age but should not trigger a new “current conditions” notification.
- Keep the source adapter separate from alert policy and Discord delivery so source semantics can be corrected without changing subscription behavior.

## Remaining research questions

- Does the published LRV product follow the fixed completed three-hour timing described in the older multi-station method page?
- Is the public derived TXT product permitted for this noncommercial automated use, and what precise attribution is requested?
- What markers besides `x` occur, can prior intervals be revised, and is there a documented update schedule or supported interface?
- A direct observatory numerical feed with clearer semantics/terms would be worth revisiting if published; none was verified in this investigation.
