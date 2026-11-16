# Compare, sweep, and export in the browser

## Compare saved backbones

1. In the analysis view, filter a scored network and select **Save this
   backbone**.
2. Change the method or filter settings and save a second result. To follow
   the [browser tutorial](first-session.md), use two distinct retained
   fractions, such as 0.25 and 0.75.
3. Open **Compare**, select the results, and run the comparison.
4. Inspect single-result measures, pairwise overlap or score alignment.
   When values are unavailable, read the explanation in the result view.
5. Download an individual table or chart, or use **Export full experiment**
   to save the comparison bundle.

Overlap and ranking answer different questions. Two runs with identical
scores and different cutoffs can agree on the ranks and still choose
different edges. See [reading comparison tables](../python/compare.md).

## Explore settings with a sweep

Open **Sweep** from the analysis workspace. A sweep configuration names one
method and one filter. You can add more configurations with independent method
and filter choices. Mark the settings to vary and enter the candidate values
for each setting. For example, with **Keep a fraction**, vary **Retained
fraction** over `25%, 75%`.

Choose **Review runs** to inspect the combinations and select the run button
to execute them. Each setup expands all combinations of its own varying
settings. The browser allows at most 100 runs in a sweep. In **Sweep results**,
choose a measurement, review the chart or table, and read the explanations
for failed or unavailable values. Download run and metric CSV files,
settings JSON, or the full experiment ZIP.

## Choose what to download

| Need | Download |
| --- | --- |
| Inspect an extracted graph | GraphML or GEXF for the backbone or annotated original graph |
| Rerun scoring and filtering | Settings JSON plus the original input and its loading choices |
| Analyze a comparison or sweep offline | CSV for the measurements or a full experiment ZIP |
| Keep a record of an analysis | The full experiment ZIP, containing a manifest, deterministic Markdown and JSON reports, settings and tables, with graph exports for an extraction |

The preview and on-screen statistics may show a subset for larger networks.
Use the exported tables and graphs when you need all rows. The
[reproducibility guide](../python/reproduce.md) describes the bundle structure.
