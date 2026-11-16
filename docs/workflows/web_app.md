# Local Web App

The local web app is a lightweight interface for guided extraction and
comparison without adding web-framework dependencies to the core package.

Run it from the repository root:

```bash
python -m netbone.webapp
```

The default address is:

```text
http://127.0.0.1:8765/
```

The console script is equivalent:

```bash
netbone-web
```

To use the Link Prediction Isolation Forest method in the web app, install and
launch the app from an environment containing the optional `ml` extra:

```bash
pip install -e .[ml]
python -m netbone.webapp
```

## Home Page

Netbone starts in light mode. Choose **Dark theme** to switch to dark mode
or **Light theme** to switch back. Netbone remembers your choice in the browser.

Choose **Open a network** to select a file or drop one network file onto
the upload area. **Try an example** reveals the weighted, unweighted, and
temporal examples. Choose one to open it directly in the analysis workspace.
If you return home with a network loaded, **Back to analysis** reopens that
workspace.

## Guided Extraction

The analysis workspace gives scoring and retention controls their own
panel beside the network preview. On narrow screens, the preview sits below the
controls.

```text
Open a network -> Score and adjust retention -> Save backbones -> Compare
                              |
                              +-> Test a range of values
```

The workspace header shows the network name, node and edge counts, direction,
and weight setting. Uploading a file opens a review of the detected mapping.
For weighted inputs, choose **Strength** when higher weights mean stronger ties
or **Distance or cost** when higher weights mean longer or costlier connections.
This choice sets the default weight handling for shortest-path methods.
Choose **Use this mapping** once the input is valid to open the method picker.
Use **Network settings** to revisit the mapping. **Change mapping** opens the input
format and column controls.
Expand **Source preview** to inspect sample rows or **Describe this network**
to add optional context. The confirmation button remains visible while you scroll.

**Choose method** opens the searchable catalog, with filters for target, approach, and network
support. Selecting a method computes scores with its default settings. Once
scores are ready, **Choose filter** opens with the recommended filter and
alternatives. Filter settings and the live
preview appear after you choose a filter. The action bar stays visible as the
workspace grows. **Inspect score distribution** shows which plotted scores pass a
score cutoff or an uncorrected significance level. On narrow screens, use
**Jump to graph** to reach the preview and **Back to filter** to return to the
settings. Hover, focus, or tap a **?** for
details about a method, filter, or preview value. Use **Save this backbone** to
keep a result for comparison, or **Inspect & export** to see details and
downloads.

**Sweep** tests a range of values on the same network. After scoring, it
starts with the current method and filter settings. Under **What to vary?**,
choose a setting and enter the values to test, such as `25%, 50%, 75%` or
`0.25, 0.5, 0.75` for retained fraction. Add another setting or an independent
setup if your experiment needs one. Remove the varying setting to run a fixed
baseline once. **Review runs** shows the actual configurations, then **Run**
executes them. Run names show the setup and the values that vary within it.
Hover over, focus, or tap a chart point to see its run names.
After saving two backbones,
**Compare** appears in
the action bar. **Back to analysis** returns to the current network and
retention controls.

The browser interface accepts built-in examples, a local CSV file, or a local
GraphML file. Static mode maps source, target, and optional
weight columns and lets the user declare whether rows are directed arcs.
After a directed CSV or GraphML input is recognized, network settings let the
user preserve its arcs or create an undirected projection before scoring.
Projection requires a visible `sum`, `mean`, `max`, or `min` rule for the
selected weight on reciprocal arcs. Unweighted projections require no numeric
merge. The updated edge and component counts, method compatibility, scoring,
filtering, and exports all use the projected network.
Temporal mode additionally maps a required time column and an
optional event-weight column, then exposes the registered temporal weighting
functions and their parameters. GraphML mode reads topology directly from the
file and offers complete numeric edge attributes as optional method weights;
source and target mapping is unnecessary. After loading data, the user may
record what nodes, edges, weights, weight direction, and time represent in the
optional context section. Netbone uses
these structured fields to explain what each method's high scores, low
p-values, or binary selections mean in that network; this workflow has no LLM
dependency.

Every registered method appears in one searchable catalog. Target, approach,
network-support, and current-compatibility facets narrow the catalog without
forcing methods into one exclusive group. Approach tags overlap when a method
uses more than one source of evidence. Compatible methods sort before
incompatible methods. Compact method rows contain only the method name and the
meaning of their first score interpretation; factual properties and
configuration remain in the selected-method pane. Ranking methods explain
higher or lower values, p-value methods
explain lower statistical values, and structural selectors explicitly identify
their `1/0` output as binary rather than a continuous ranking. Methods
incompatible with the selected weight or graph direction remain visible with
an actionable reason and cannot be scored. Essential method parameters remain
visible while parameters marked advanced are collapsed initially. Discrete
choices use compact diagrams to show how each option changes the statistic.

Temporal rows are loaded with `nb.from_temporal_edgelist(...)` and aggregated
with `nb.aggregate_temporal(...)` before the ordinary pipeline runs. Network
settings let the user declare whether source-to-target event direction matters.
Repeated undirected pairs become one edge; in directed mode repeated ordered
events become one arc and reciprocal arcs remain distinct. Both produce a
canonical `weight`. A directed aggregate can remain directed or use the same
explicit reciprocal-merge projection offered for other directed inputs. When
no event-weight column is selected, every event has magnitude `1.0`, so
weighted methods can still use the resulting aggregate weight.

Baseline and ASF expose snapshot controls. Persistent exponential, Weibull,
and log-logistic weighting instead expose required memory parameters and an
elapsed-time unit. Datetime events require that unit; numeric event times use
their native unit when it is omitted. Snapshot controls are disabled for these
kernels because their formulas use exact, potentially fractional elapsed ages.

The **Network settings** dialog shows parsed rows beside the detected mapping and
readiness summary. The full mapping form appears when validation fails or the
user chooses **Change mapping**. Readiness reports node, edge, and
connected-component counts, direction, and whether weights are active.
Validation and likely-weight warnings remain visible in the workspace before
scoring is enabled.

GraphML input is loaded through `nb.from_graphml(...)`, so direction is detected
from the file and reciprocal arcs are preserved. Directed graphs currently
enable Disparity, LANS, Link Salience, Link Prediction, Link Prediction
Isolation Forest, and Noise Corrected. Other methods remain visible but disabled with an
explanation. An explicit undirected projection enables the registered
undirected methods. For reciprocal arcs, the selected finite numeric weight
uses the chosen merge rule;
conflicting direction-specific attributes remain available as directional
provenance. Multigraphs, multidigraphs, and self-loops are rejected.
Existing node and edge attributes are otherwise preserved. A selected weight
attribute must have a finite numeric value on every edge.

Because the server is a local process, Netbone does not impose an application
upload-size limit. Available memory and browser performance remain the
practical limits for large files.

Filters are presented only after scores are computed. The user can then explore
the compatible retention rules in the terminology of the current network.
Threshold and significance controls use the observed range of the computed
primary statistic and combine a slider with exact numeric entry. When extreme
tails would compress most scores, the distribution defaults to **Dense values**
and reports how many extremes are outside the displayed range; **Full range**
restores the complete axis. Both views use the same scores and filter boundary.
For p-value methods, lower values mean stronger evidence and significance keeps
the strict `p < alpha` comparison. Method warnings remain visible beside the
score distribution.

Changing a cutoff, alpha, fraction, tie policy, or operator updates the preview
from the cached scores. The preview shows backbone nodes, edges, and connected
components (weakly connected components for directed networks). Counts reflect
the full network. For networks over 80 nodes or 1,000 edges, the drawing is
unavailable. Counts and graph export remain available.
Node colors identify
components in the backbone, including weak components for directed graphs.
Isolated backbone nodes are gray. The node and edge cards show counts and
percentages relative to the original network. For edge selections, the node
card counts only nodes that touch a backbone edge.

On wider screens, **Inspect & export** puts graph and JSON downloads side by
side. The full experiment has its own row above the statistics table.

- **Download graph** saves the retained backbone or the annotated original in
  GraphML or GEXF.
- **Reproduce this analysis** shows the resolved configuration and JSON download.
  Temporal runs include temporal aggregation and pipeline configuration.
  Directed-to-undirected runs include the projection mode and reciprocal merge
  rule.
- **Export full experiment** downloads a ZIP with the graphs, statistics,
  pipeline settings, report, and manifest. Its `web_settings.json` records the
  network context and resolved settings, including temporal aggregation or
  direction conversion when used.
- **Inspect statistics** shows the endpoints and input weight, when available,
  before the computed statistics and retention status. The CSV uses the same
  column order.

## Compare Backbones

Each saved backbone receives a short label based on its method and filter.
Adjust the filter or choose another method on the same network, then save a
second backbone to unlock **Compare**. In Compare, select at least two saved
backbones. Drag a card by its grip to change the order for the next comparison,
or focus the grip and press Up or Down. You can rename or inspect each backbone from the list. The rename
dialog can restore a suggested short label. Saved results remain
available while method and filter choices change. Opening another dataset starts
a new saved list.

**Compare backbones** delegates to `nb.compare(...)` on the local Python server.
The saved-backbone list grows with the page. Its inspection action shows the
exact method, filter, and parameters. Choose **Download configuration** to save
that backbone's resolved pipeline as JSON, or **Statistics** to see retained
and rejected items. After running the comparison, choose **Export full
experiment** to save the compared backbones' labels and settings together with
the results. Use the same input network when reproducing the comparison.
The browser presents one
metric or pair at a time. Choose **Properties**, **Overlap & agreement**, or
**Score alignment**, then pick a metric or pair. Switch between **Chart** and
**Table** to see the underlying records:

- per-result retention, count, weight, and connectivity metric records;
- pairwise node/edge overlap and importance-oriented Spearman records;
- aligned raw values and importance ranks for each compatible result pair.

Every registered comparison metric is requested. Metrics that do not apply are
shown as `invalid` or `undefined` rows with the package explanation instead of
being omitted or stopping other metrics. For example, undirected results retain
the explanatory invalid rows for weak and strong connected-component metrics,
and edge-to-node score comparisons retain an invalid Spearman row. Directed
comparisons preserve ordered arc identity, including reciprocal arcs.

Backbone properties use accessible SVG horizontal bars with a consistent color
for each saved result. Pairwise properties use an SVG symmetric matrix; overlap
measures use a sequential scale, while importance-rank agreement uses a
diverging scale from opposite to matching rankings. Invalid and undefined
records remain visible in the figure rather than becoming numeric marks. Each
active chart can be downloaded as SVG or a two-times-resolution PNG. Each saved
backbone keeps an **Inspect statistics** action for its method values and
retained/rejected selection. The property CSV download exports the exact
records behind the active view. Formatting such as percentages is display-only;
downloads preserve the values returned by the public comparison API.

Score alignment uses one point per aligned node or edge and plots the two
importance ranks. Larger ranks always indicate greater method-specific
importance, including mixed score-versus-p-value comparisons. A diagonal
reference line marks equal ranks, point tooltips retain raw values, and the
selected pair's importance-oriented Spearman coefficient and target-appropriate
backbone Jaccard overlap appear above the plot. Wheel or button zoom, pointer
dragging, and reset controls support dense alignments without changing the
underlying records. Incompatible pairs remain selectable and show the package
explanation instead of an empty or misleading chart.

The interface includes empty, running, success, validation, and error states,
keyboard-accessible dialogs, labelled tables and graph preview, and
responsive layout rules for narrower screens.

The server delegates analysis to the public package API. The split browser path
matches the public score/filter separation:

```python
network = nb.from_graph(...)
scores = nb.pipeline().score(method_name, **method_parameters).compute(network)
result = nb.filter_scores(network, scores, filter_name, **filter_parameters)
```

For temporal input, reproduce the aggregation before running the same pipeline:

```python
temporal = nb.from_temporal_edgelist(
    "events.csv",
    time="time",
    event_weight="magnitude",
    directed=True,
)
network = nb.aggregate_temporal(
    temporal,
    weighting="asf",
    p=3,
    q=0,
    a=5,
)
result = pipeline.run(network)
```

For GraphML input, load the graph directly before running the resolved pipeline:

```python
network = nb.from_graphml("network.graphml", context="...")
result = pipeline.run(network)
```

For an undirected projection, reproduce the preprocessing step explicitly:

```python
network = nb.from_graphml("network.graphml", context="...")
network = nb.to_undirected(
    network,
    weight="strength",
    reciprocal_merge="sum",
)
result = pipeline.run(network)
```

The web layer stays thin. It adapts form input, renders summaries, and returns
validation errors, while method scoring, filtering, measurement, comparison, and
reporting remain in the package API.

## API Endpoints

The local server exposes JSON analysis endpoints and one binary export endpoint:

- `GET /api/ui-schema` returns the method catalog, overlapping discovery
  facets, contextual score-meaning templates, score-interpretation types,
  temporal weighting controls, and form-control definitions. It also advertises
  optional server capabilities so the browser can disable controls that an
  older local server does not support.
- `GET /api/registry` returns raw registered method, filter, and temporal
  weighting metadata.
- `POST /api/preview` accepts guided data controls and returns parsed-data
  readiness, suggestions, warnings, errors, counts, and preview rows.
- `POST /api/score` accepts guided score controls, computes method statistics,
  stores them in a small local in-memory cache, and returns a score id,
  statistics rows, score ranges, and a method-only pipeline config.
- `POST /api/filter` accepts a score id plus guided filter controls, reuses the
  cached method result, stores the completed extraction in a bounded local
  result cache, and returns a result id plus the resolved pipeline config.
- `POST /api/filter-preview` accepts the same cached score id and filter
  controls. It returns exact selected-item, node-coverage, and output-node
  counts and fractions, the resolved draft configuration, and a graph sample
  of up to 80 nodes and 1,000 edges. It reuses the cached method scores.
- `POST /api/compare` accepts at least two uniquely labelled result ids and
  returns every registered single-result and pairwise metric plus valid or
  invalid score-alignment pairs as tidy records.
- `POST /api/sweep` accepts the imported dataset, named method/filter
  configurations with fixed or varying parameters, and selected metrics.
  It delegates to `nb.sweep(...)` and returns generated pipeline configurations,
  tidy run and metric records, setup names, failures, and score-cache counts.
  A preview request resolves configurations without executing them.
- `POST /api/export` accepts a completed result id plus graph format and scope,
  then returns an attachment containing GraphML or GEXF.
- `POST /api/run` accepts guided controls and returns the one-shot extraction
  result, a result id, and the resolved pipeline config.

## Supported Workflows

- CSV and TSV edge-list input;
- temporal CSV and TSV event-list input and aggregation;
- local GraphML upload with numeric edge-attribute weight selection;
- guided weighted and unweighted examples;
- built-in temporal CSV example;
- source, target, weight, time, event-weight, and delimiter controls;
- explicit directed-arc control for static CSV data and automatic GraphML
  direction detection;
- optional directed-to-undirected projection before method selection, with an
  explicit reciprocal weight merge rule for weighted inputs;
- baseline and ASF snapshot weighting plus persistent exponential, Weibull, and
  log-logistic exact elapsed-time weighting;
- explicit guided-example or own-dataset starting choice;
- a single workspace for the current network, with Compare and Sweep available
  from relevant analysis actions;
- responsive workspaces that stack controls and results on narrow screens;
- structured node, edge, weight, weight-direction, and time context;
- deterministic contextual score interpretations without an LLM;
- live data-readiness summary and parsed-row preview;
- node and edge counts before run;
- connected-component counts for undirected graphs and weak/strong component
  counts for directed graphs;
- weight auto-detection and weight-related warnings;
- visible blocking for methods that require weights when no weight is selected;
- visible blocking for methods that do not support a directed input;
- disabled method controls, with an explanation, when a supported method ignores
  that parameter for directed input;
- readiness-controlled score/filter availability;
- one searchable catalog containing every registered method with target,
  approach, network-support, and compatibility facets;
- searchable method library that opens from **Choose method**;
- factual target, weight, and statistic details in the selected-method pane;
- selected method summary with target, statistic, direction, and weight
  requirement;
- score-first compatible-filter catalog and guided controls;
- selected filter summary;
- visible illustrated method parameters and filter controls;
- method-aware threshold defaults;
- dense-values and full-range score views derived from computed statistics,
  with exact numeric cutoff entry;
- score distributions synchronized with threshold, significance, and fraction
  controls;
- exact live retention, node coverage, and output-node counts alongside a
  bounded graph preview while tuning filters;
- separate score computation and filtering actions;
- local score reuse while filter controls are adjusted;
- server-side pipeline resolution;
- a backbone details dialog for export, statistics, and reproducibility;
- original-network and backbone context shown together;
- result summary cards;
- method statistics table with retained/rejected status;
- primary statistic and filter statistic labels;
- statistics CSV download;
- warnings and validation errors;
- small SVG network preview;
- arrowheads for directed graph previews;
- graph retained/rejected legend;
- annotated-full-network and backbone-only GraphML downloads with deterministic
  target color and computed method-statistics columns;
- equivalent GEXF downloads with Gephi-readable color and size or thickness
  metadata and computed method statistics;
- resolved pipeline config after each run;
- combined temporal aggregation and pipeline config for temporal runs;
- resolved direction-conversion and pipeline config for projected runs;
- resolved pipeline config download;
- labelled saved extractions from the current imported network;
- selectable per-result and pairwise comparison through `nb.compare(...)`;
- compatible score-alignment scatterplots with raw-value table and CSV access;
- configuration-based sweeps where each named setup chooses its own method,
  filter, fixed parameters, and varying parameter ranges; configurations are
  expanded independently rather than being crossed with unrelated setups;
- access to Sweep as soon as the network is ready, with the current resolved
  method and filter settings carried over after scoring;
- an inline sweep editor for choosing settings and entering values. Base and
  fixed settings and measurement choices open on demand;
- a separate **Review runs** screen that shows the varied values and exact
  configurations. After the sweep, **Run settings** opens the settings for
  each completed run;
- generated-run counts and exact pipeline review before execution, with
  selected metrics, explicit failures, score-reuse counts, and
  run/metric/config downloads;
- sweep trajectory charts for numeric method or filter parameters, and
  retention-versus-connectivity plots for measured runs; both have setup and
  metric selectors, table/CSV fallbacks, and SVG/PNG figure downloads;
- selected CSV or temporal weight columns carry into generated sweep method
  configurations when a method accepts a weight parameter; explicit method
  weight settings remain authoritative;
- explicit invalid and undefined metric explanations;
- inspectable saved method statistics and selections;
- plot-ready single-result and pairwise comparison CSV downloads;
- empty, loading, success, validation, and error states;
- keyboard tab navigation and accessible labels;
- responsive layout polish for desktop and mobile widths.

After a comparison or sweep finishes, **Export full experiment** saves a ZIP
of that run. Both bundles include a report, manifest, and pipeline settings.
Compare includes the selected backbones in comparison order, metrics, and score
alignment records. Sweep includes generated configurations, setup names, run
metrics, and the explanations for any failed configurations. Keep the original
network data to rerun the pipelines. If a completed run is no longer available
to download, run it again to create a new ZIP.

## Frontend Development

Package users do not need Node.js. The wheel contains the compiled HTML, CSS,
and JavaScript served by the standard-library Python server.

Frontend contributors edit the React and TypeScript source under `web/`. From
the repository root, install the locked development dependencies and rebuild
the packaged assets with:

```bash
npm ci --prefix web
npm run build --prefix web
```

The Vite build writes deterministic filenames directly to
`src/netbone/webapp/static/`. Run `python -m netbone.webapp` afterward to review
the production build through the same server used by installed packages.

With the Python package installed and the frontend built, run the browser
smoke test from the repository root:

```bash
npx --prefix web playwright install chromium
npm run test:browser --prefix web
```

The test starts its own server on port 8795, uploads a weighted CSV, confirms
the mapping, and downloads ZIPs from extraction, comparison, and sweep at
desktop and narrow viewport widths.
The compatibility tests use Node Degree on an unweighted CSV and Disparity on
a directed temporal example through extraction, comparison, and sweep. They
also check that the method picker explains and disables incompatible choices.
The method matrix runs each compatible method with its recommended filter on
directed and undirected weighted, unweighted, and temporal networks.
Install Netbone with its `ml` extra to include Link Prediction Isolation Forest.
Marginal Likelihood requires positive whole-number weights. For temporal
data, Baseline weighting with whole-number event magnitudes can meet this
requirement.
Noise Corrected has the same count-weight requirement. Its recommended cutoff
is 1.64 standard deviations above the null expectation.
The suite also checks keyboard focus in dialogs, horizontal keyboard scrolling
in the statistics table, recovery from a nonnumeric CSV weight, and GraphML
export for a network too large to draw in the preview.
It also checks that Edge Betweenness shows and exposes its scoring status
before opening the filter dialog, and records the scoring request duration
for the test network.
Set `NETBONE_WEB_COMMAND=netbone-web` to test the installed command, or set
`NETBONE_BROWSER_CHANNEL=msedge` to use a local Edge installation.
Set `NETBONE_BROWSER_PORT` if the default port is unavailable.
