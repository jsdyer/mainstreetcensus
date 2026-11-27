# Main Street Census

Compare Canadian employer-location counts across municipalities and metro areas. The [live comparison](https://coolcode.ca/mainstreetcensus/) opens on restaurants in the Township of Langley and the City of Langley. Change either place, the industry or the retained edition. The address bar preserves a completed comparison for sharing. The [public result directory](https://coolcode.ca/mainstreetcensus/records/) works without JavaScript.

<!-- coolcode:guide -->
Compare the Township of Langley with the City of Langley, then open the employee-size bands to see how their restaurant locations are distributed. The Halifax comparison illustrates the overlap between a municipality and its surrounding metro area. Place codes identify each boundary when names repeat. Industry profiles link to every included metro area and let you change either place.
<!-- /coolcode:guide -->

## Data and coverage

Statistics Canada counts operating locations on the Business Register. Chains can contribute multiple locations. This extract covers employers in selected NAICS groups across every geography with a published all-industries row or selected-industry row in the source. The province suffix and geographic ID disambiguate municipalities sharing a name. The publisher includes qualifying subdivisions outside census metro areas. Source methodology and definition notes are linked on each result.

The first saved edition is **June 2026**, published 14 August 2026 in [table 33-10-1176-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3310117601). Its title supplies the June/December reference period. The machine CSV’s generic REF_DATE is not a snapshot date. Location counts are integers. Omitted and unpublished cells display as a dash; a published zero displays as zero. Size bands count workplaces in each range. The source advises against using editions as a time series because classification and administrative changes can alter totals. The interactive comparison always draws both places from a single edition.

The [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/reference/licence) applies to the source data. A source check records the actual time the publisher catalogue and selected edition were read. **The publisher releases new tables semiannually; the collector checks monthly, at 14:19 UTC on the 15th.** Historic local extracts retain their own area and industry lists. A new snapshot from the same publication can replace that edition after a revision.

## Expand or customize

Edit `sources.json` to change the industry codes, featured seven-digit subdivision codes, names or comparison presets. Follow the exact NAICS and geography codes in the publisher's metadata CSV. All published census metro areas are profiled automatically. Each industry, featured area and comparison receives a canonical HTML page. For another edition, the collector discovers new Statistics Canada product IDs using the data table title in the WDS catalogue. Any changed dimension or unexpected observation causes a failed check before publication. Re-run with an updated reviewed mapping if Statistics Canada revises the classification.

Run `python3 scripts/refresh.py` for a live collection. A replay accepts a saved WDS response via `--catalogue FILE` and its matching official archive via `--zip FILE`. The scheduled and manually dispatchable `.github/workflows/refresh.yml` validates an extract, commits it and invokes the native Pages workflow. Its separate schedule guard watches the collector. A failed source check keeps the last published edition. `data/status.json` exposes the check timestamp, edition and published area count for the catalogue and independent watchdog.

Build offline with `python3 scripts/build.py`. Run `python3 -m unittest discover -s tests -v`, `node --test tests/*.test.mjs`, and `python3 tests/browser_smoke.py` after installing the test-only Playwright dependencies. Push validated source to main to publish through Pages. Open `dist/` through an HTTP server to preview. Location selections stay in the browser and its URL; there is no account, saved preference or form submission to an external service. Tool metrics follow CoolCode’s aggregate counting policy.
