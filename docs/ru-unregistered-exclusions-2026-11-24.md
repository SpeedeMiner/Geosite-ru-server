# Reviewed unregistered RU removals — 2026-11-24

> Historical record: superseded on 2026-11-25 by the Light-following policy. The separate 29-name list and blocking coverage gate have been removed; the Light release now controls these exclusions and restorations. See README for current behavior.

Server rolling synchronization failed on 2026-11-25 ([run 45532503326](https://github.com/SpeedeMiner/Geosite-ru-server/actions/runs/45532503326)): the verified new Light DAT removed 29 suffix rules, while Server allowed only the historical Habr removal.

The exact 29 names are pinned in `tools/project_geosite.py`, matching [Light PR #47](https://github.com/SpeedeMiner/Geosite-ru-light/pull/47) and its [registration preflight](https://github.com/SpeedeMiner/Geosite-ru-light/actions/runs/45459256012). The previous Light rolling DAT SHA-256 was `027939e3a31591bd48a57428c893a8237fe61352d90a8c3077b39366a3a3d0cc`; the reviewed new DAT SHA-256 is `5a4f6b76814571995b36fe37f0613c0e856da9c98943e74f8313f77fa148ffc8`.

The projection excludes these apexes, their descendants and encompassing suffix rules. The coverage gate permits only the 29 exact ROOT/suffix losses and the existing Habr exception, never additional FULL or unrelated losses. Reintroduced coverage is rejected even after the previous rolling release has incorporated the removals. Private exclusions, required roots, retained Server suffixes and SHA-256 checks remain intact.

This policy applies to newly built projections; existing numbered releases are immutable and the numbered workflow still skips when no newer Light numbered release exists. Registration may change: revisit individual exceptions on evidence that a legitimate service has returned, through a reviewed policy change. This was the policy before the subsequent Light-following change.
