# Ionospheric critical frequency above Iceland

Researched on 2026-11-01. This is source research for a possible future bot query/alert feature; no implementation or source selection has been approved by this note.

The user subsequently selected the KC2G estimate for a private query command. `/fof2 nuna` now reports an estimate near Reykjavík; see the README for implemented behavior. Alerts remain outside the feature.

## Finding

The relevant quantity is **foF2 in MHz**, the F2 layer ordinary-mode vertical critical frequency. A current, publicly accessible numerical **measurement above Iceland** was not verified. However, a numerical **estimate for an Icelandic location** was successfully obtained from KC2G's assimilated model grid. This is the best working integration candidate found for the requested geography, provided the reply explicitly says “estimated.” Historical Reykjavík observations and current foreign-station readings are separate products.

[WMO OSCAR defines foF2](https://space.oscar.wmo.int/variables/view/fof2) as the F2 layer critical frequency, measured in MHz and associated with peak electron density. It is distinct from the maximum usable frequency for a specified oblique path, from sporadic-E critical frequency foEs, and from integrated total electron content (TEC). A foF2 reading alone does not establish whether a particular HF path or band is usable.

## Iceland stations and historical evidence

| Candidate | Evidence | Consequence |
| --- | --- | --- |
| Reykjavík, **RKA64**, 64.1° N, 21.8° W | [NOAA UAG-091 station catalogue](https://www.ngdc.noaa.gov/stp/space-weather/online-publications/stp_uag/uag-091.pdf), Table 5, gives geographic co-latitude 25.90°, east longitude 338.20°, and open/close dates April 1944–December 1964. [UKSSDC station catalogue](https://www.ukssdc.ac.uk/gbdc/station-list.html) independently lists RKA64 at the same coordinates. | A valid historical Iceland station, not evidence of a live feed. Coordinates are catalogue precision, not a surveyed present instrument location. |
| Garður / Reykjanes / Blönduós | No operating Iceland ionosonde numerical feed or URSI identifier was verified. [Iceland Space Park’s own instrument-hosting page](https://www.geimgardur.is/weather.html) describes how an ionosonde *could* supply North Atlantic conditions and invites instrument proposals. | Hosting proposals do not establish an existing ionosonde or its data availability. |
| Gakona, **GA762** | [Lowell’s station list](https://ulcar.uml.edu/framesn.htm) locates HAARP/Gakona in Alaska at 62.24° N, 214.91° E (145.09° W). | Gakona is not an Iceland station. |

NOAA’s catalogue dates describe the historical entry; they cannot prove that no private, later, or unlisted Iceland instrument exists. This investigation found no evidence sufficient to claim a current Iceland measurement service. Lowell’s accessible legacy station list itself says “Last update: August, 2005”; its station entries must not be used as a current operations register.

## GIRO / Lowell DIDBase

[GIRO](https://giro.uml.edu/) and its [IonoWeb station browser](https://giro.uml.edu/ionoweb/) are the main leads for ionograms and scaled station characteristics. The [GIRO SPASE registry record](https://spase-metadata.org/ISWI/Observatory/GIRO.html) describes Digisonde measurements of the bottomside ionosphere, public DIDBase access, and submission within several minutes at 37 real-time sites. That record was revised in 2023 and is descriptive metadata, not a verified current availability or latency guarantee.

Direct access checks on 2026-11-01 did **not** establish a working numerical integration:

- `https://giro.uml.edu/ionoweb/`, the scaled-data page `https://giro.uml.edu/didbase/scaled.php`, and rules pages failed TLS verification locally or timed out in the web fetcher. TLS verification was kept enabled.
- A complete candidate numerical query, [DIDBGetValues for Tromsø foF2 on 2026-11-01](https://lgdc.uml.edu/common/DIDBGetValues?ursiCode=TR169&charName=foF2&fromDate=2026.11.01&toDate=2026.11.02), repeatedly returned HTTP 404. This was an actual HTTPS request, not a search snapshot.
- Therefore the candidate route must be revalidated through the provider’s current documentation/interface before implementation. No numerical sample, documented API stability, request limit, station-specific cadence, or Iceland station support was verified from this endpoint.

The [SPASE record](https://spase-metadata.org/ISWI/Observatory/GIRO.html) requires acknowledgement of both data suppliers and Lowell and directs users to [Rules of the Road](https://giro.uml.edu/didbase/RulesOfTheRoad.html) and the [acknowledgements list](https://giro.uml.edu/didbase/acknowledgements.htm). Those linked pages were not successfully retrieved in this session. A general open-data licence or automated redistribution permission is therefore **not confirmed** here. Public reachability and the repository licence do not resolve provider terms.

For future integration, preserve provider quality/qualifier fields and whether the record is automatically or manually scaled. The meaning of every numerical API quality field remains to be verified against an accessible primary specification; this note deliberately does not promote a third-party description of confidence scores into a provider guarantee.

## Verified regional source: Tromsø / Ramfjordmoen, Norway

[UiT’s current ionospheric-soundings description](https://site.uit.no/spaceweather/data-and-products/ionospheric-conditions/ionospheric-soundings/) identifies its Digisonde outside Tromsø and a separate CADI in Ny-Ålesund. [TGO’s source page](https://geo.phys.uit.no/ionodata/index.html) links current ionograms and archives. These are regional observations, not measurements above Iceland.

A direct fetch of the [latest Ramfjordmoen ionogram PNG](https://geo.phys.uit.no/ionosonde/latest.png) at approximately **2026-11-01 22:29 UTC** returned HTTP 200. The image itself showed:

```text
Station: Tromso / tr169
Location printed on image: 69.66 N, 19.2 E
Observation: 2026-11-01 22:15:00
foF2: N/A
MUF(D): N/A
Auto: Artist5
C-level: 22
```

HTTP `Last-Modified` was `Sun, 01 Nov 2026 22:23:01 GMT`. Observation time, file modification time, and fetch time are different. This is a useful verified example of **freshly delivered data without an available foF2 measurement**, not a numerical critical-frequency sample. Another printed quantity, `foEp=0.45`, must not be substituted for foF2. The [display page](https://geo.phys.uit.no/ionosonde/) refreshes its browser every 120 seconds; this does not establish measurement cadence or guaranteed publication latency.

The directly linked [1932–2024 noon foF2 text archive](https://geo.phys.uit.no/ionodata/Tromsoe_ionosonde_foF2_1932_2024_noon_v18.txt) returned HTTP 200 with a whitespace table headed `% YYYY MM DD datenum foF2`. It contains old daily data, including `0.00` entries whose sentinel semantics were not documented in the inspected material. It is unsuitable for present-condition alerts. No current machine-readable numerical UiT foF2 endpoint was verified. Reading chart pixels is not a reliable production numerical interface.

## Alternatives investigated

- [Lerwick ionosonde](https://www.ionosphericmonitoring.rl.ac.uk/ionosondes/lersite.html) is explicitly described by its operator as closed. Its geographical usefulness does not make historical data current.
- [UKSSDC world ionosonde browser](https://www.ukssdc.ac.uk/wdcc1/ionosondes/world.html) is useful for station and archive discovery. Data selection encountered authentication prompts; an anonymous current Iceland numerical feed was not established.
- [Australian Space Weather Forecasting Centre global foF2 map](https://www.sws.bom.gov.au/HF_Systems/6/5/1) is a lead for a mapped global product. A verified Iceland numerical point API and its precise observation/model provenance were not established in this investigation.

## Verified numerical estimate: KC2G global model

The [KC2G foF2 map](https://prop.kc2g.com/fof2/) offers geographically relevant estimates for Iceland. Its [own explanation](https://prop.kc2g.com/about/) distinguishes measured station dots from interpolated values elsewhere, describes maps every 15 minutes based on observations usually 5–20 minutes old, and notes greater uncertainty far from stations. It uses GIRO data and an IRI baseline. This is a model product; geographic coverage is not evidence of a measuring instrument at that point.

Actual public HTTPS requests succeeded for:

| Endpoint | Verified result | Use |
| --- | --- | --- |
| [`/api/latest_run.json`](https://prop.kc2g.com/api/latest_run.json) | JSON run identifier, start/target times, and map timestamps | Select/check model valid time and distinguish current estimates from future forecasts. |
| [`/api/assimilated.h5`](https://prop.kc2g.com/api/assimilated.h5) | HDF5 grid, 397,166 bytes in the sampled response | Obtain numerical foF2 over Iceland; no chart scraping required. |
| [`/api/stations.json?maxage=3600`](https://prop.kc2g.com/api/stations.json?maxage=3600) | JSON observations from 28 stations in that sample | Optional named-station context, preserving age and confidence information. This is a relay, not a directly verified GIRO endpoint. |

The provider's [API implementation](https://github.com/arodland/prop/blob/master/api/app/main.py) defines these routes and allows the grid download to be pinned using `run_id` and `ts`. Prefer a single grid with its embedded `/ts`, or pin a run/time if fetching multiple associated resources, so an update between requests cannot mix model runs. The default grid is the latest nowcast; future maps are a distinct product.

### Successfully extracted Iceland example

The metadata response identified run `89415768`, started **2026-11-01 22:25:02 UTC**, with target/valid time **2026-11-01 22:30:00 UTC**. The HDF5 file's `/ts` independently matched that valid time. Its `/maps/fof2` dataset has shape `(181, 361)`. The provider's [grid-generation source](https://github.com/arodland/prop/blob/master/assimilate/app/assimilate.py) defines one-degree latitude points from -90 to +90 and longitude points from -180 to +180, indexed latitude first.

- Grid point **64° N, 22° W**: foF2 **3.6751986 MHz**.
- Bilinear interpolation of the surrounding four grid points at an example Reykjavík coordinate, **64.15° N, 21.94° W**: **3.6747786 MHz**.
- Sensible display: **“Áætluð foF2 við Reykjavík: 3,7 MHz — 2026-11-01 22:30 UTC.”** The extra digits above document the extraction, not justified observational precision. This dated sample is not a present-time report or band-opening claim.

Reading the sampled grid required `h5py`, `numpy`, and `hdf5plugin`: the file uses SZ compression (HDF5 filter 32017), so plain h5py could read metadata but could not decode grid values by itself. These packages were installed only in the local research environment; the bot's project dependencies and code were not changed. A future integration must account for image size and available wheels on its deployment architecture.

There is also a `/stdev/fof2` grid. The assimilation source fits logarithmic residuals, so this field must not be presented directly as a ±MHz error bar. A calibrated uncertainty interpretation for Iceland has not been verified. The embedded station metadata can include old observations; its mere presence does not prove those observations were used or that they are fresh.

### Station context and quality

At the time of the sampled station request, the closest returned fresh station to that Reykjavík coordinate was Tromsø, **TR169**, approximately **1,854 km away**, with foF2 **4.7 MHz** at **2026-11-01 22:22:30** and `cs=60`. The next was Juliusruh, **JR055**, approximately **2,226 km away**. Distances are great-circle calculations using the API's station coordinates, not provider claims. No Icelandic station appeared in this one-hour result set; that is not a census of all operating instruments.

The JSON uses a separate `time`, `fof2`, `cs`, `source`, and nested station object. It also returned confidence values of `0` and `-1` for some stations, while embedded grid metadata uses a different-looking scale. Preserve raw quality fields and verify their interpretation before choosing an alert confidence threshold. These raw observation timestamps omit an explicit timezone suffix; confirm their UTC convention before production use. The grid `/ts` Unix timestamp is unambiguous.

### Access limits

The tested API responses required no credentials. A supported service contract, explicit automated-use quota, and licence for redistributing model values were not verified. The [acknowledgements page](https://prop.kc2g.com/acknowledgments/) identifies upstream contributors. Attribute both the model provider and the upstream data as appropriate, and confirm expectations before sustained polling. The public source repository is useful evidence of the API/schema; do not infer a right to copy its code from GitHub visibility alone.

## Implementation implications

These are engineering recommendations, not provider statements:

- Decide explicitly whether the feature should report an **estimated foF2 at an Iceland coordinate** or a **measured foF2 at a named foreign station**. The former is the more geographically relevant option when direct Iceland measurements are unavailable, but must say “estimated.”
- Every reply should show MHz, location/station, observation or model valid time, source and age. Store fetch time separately.
- Do not replace missing foF2 with foEs, foEp, fxI, MUF(3000), TEC, or a forecast without changing the product label. Distinguish unavailable, stale and source failure.
- Start with an estimated foF2 query at a named/default Icelandic coordinate using the verified model grid and link its map. Keep a named foreign-station measurement separately labelled if included. Default coordinates, command name and alert behavior are future product decisions.
- Before alerts, verify missing markers, quality interpretation, operational reliability and usage expectations. Suppress stale/missing/low-quality records and deduplicate the same model valid time. Threshold crossings should have persistence or hysteresis to avoid repeated notifications from noise or changes to the interpolation inputs. An estimate crossing 7 MHz is not a guarantee of usable 40 m NVIS.
- Poll at a modest interval consistent with the chosen provider, with timeouts, caching and backoff. KC2G's nominal 15-minute maps suggest caching by model valid time; a production poll interval is not selected by this research.
- Treat any claim that a particular HF path “is open” as a separate propagation question requiring more than foF2.

## Remaining research questions

- Can GIRO provide a supported, currently reachable numerical endpoint and current station list, with quality documentation and redistribution terms?
- Does any Iceland institution now operate an ionosonde with public foF2 measurements beyond the historical RKA64 record?
- Can KC2G confirm automated-use expectations and a supported schema/interface for model-grid access? How well is its interpolation calibrated over Iceland, and what uncertainty/quality gate would be appropriate for alerts?
- Which nearby stations actually deliver fresh numerical foF2 reliably over several days? A single successful page or missing-value sample does not establish operational reliability.
