# units' website

The page for the units library, live at https://units-package.syncster.dev.

Author: Alexius Academia · Started 2026-10-30

A static page: no build step, no dependencies. Netlify (team syncster.dev)
deploys this folder by itself whenever `main` is pushed to GitHub.

```
index.html             # the page
styles.css             # chart's, csv's, inspector's and viewport's design, in rust orange
assets/app*.png        # the example app (../examples) snapshotted headless, light and dark
assets/reading.png, systems.png, temps.png, errors.png   # the example in four states, cropped
assets/share.png       # the picture shown when a link to the site is shared (1200 x 630)
assets/favicon.svg
netlify.toml           # no build; HTML isn't cached
```

To look at it locally: `python3 -m http.server 8080 -d website`, then
http://localhost:8080/.

The pictures come from `TESSEL_SCRIPT="…; snapshot file.png" tessel run examples`,
cropped with `sips -c H W --cropOffset Y X` (sips crops from the middle when
the offset is 0 0, so use 1 for a zero). Retake them after the example changes.
