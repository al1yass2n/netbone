# Troubleshooting

## Installation and startup

| Symptom | What to check |
| --- | --- |
| Import works but `nb.pipeline` is missing | Print `netbone.__version__` and `netbone.__file__`. Activate the intended environment and [install from the current checkout](start/install.md). |
| `netbone-web` is not found | Start the app with `python -m netbone.webapp` instead. The shortcut needs Python's scripts folder on your `PATH`, as in an activated virtual environment. `python -c "import sysconfig; print(sysconfig.get_path('scripts'))"` prints that folder. |
| The server reports an address-in-use error | Pick a different port with `--port`, then open that port in the browser. |
| The browser cannot connect | Check that the terminal process is running and that the address and port match the startup message. |
| Isolation Forest or plotting cannot import its dependency | Install the [ml or viz extra](start/install.md#optional-tools) in the environment running Netbone. |

## Input and scoring

| Symptom | What to check |
| --- | --- |
| "is not UTF-8 text" | Save the file as UTF-8, for example **CSV UTF-8** in Excel, and load it again. |
| "has a header but no edges" | The file has column names but no rows below them. Check that you exported the data and not only the header. |
| "Row N has M values but the header has K columns" | A row has more values than the header names. Check the delimiter (for example `;` instead of `,`, or a space-separated file read with commas), or add a header for the extra column. |
| "repeats the edge between A and B from row N" | Each edge may appear once. In an undirected file `A,B` and `B,A` are the same edge. Merge repeated rows first, for example by summing their weights, pass `directed=True` to keep both directions, or use the [temporal loader](python/temporal.md) for repeated events. |
| "has a boolean weight" | Weights must be numbers. Replace `true`/`false` with numbers, or pass `weight=None` for an unweighted network. |
| "mixes numbers and dates" | A temporal time column must hold one kind of value. Use snapshot numbers on every row or dates on every row. |
| The web app rejects an upload as too large | The local app accepts files up to 100 MB. Start it with a higher limit, for example `python -m netbone.webapp --max-upload-mb 500`. |
| A weighted method rejects the graph | Verify the selected weight attribute on each edge. Some methods require positive values or integer counts. See the [method catalog](reference/methods.md). |
| A method is incompatible with directed data | Choose a directed-capable method or make an explicit [undirected projection](python/inputs.md#preserve-or-project-directed-links). |
| Datetime events need a time setting | Provide a `snapshot_size` for snapshot weightings or `time_unit` for persistent elapsed-time weightings. See [temporal time scales](python/temporal.md#choose-the-time-scale). |

## Results and downloads

| Symptom | What to check |
| --- | --- |
| A fraction retained more items than requested | Netbone rounds the requested count up. The default policy also includes all cutoff ties. See [fraction tie policies](filters/fraction.md#ties-at-the-cutoff). |
| All input nodes remain after edge filtering | Edge filters preserve nodes by default. Use `drop_isolates=True` when only incident nodes should remain. |
| A metric is missing | Read `status` and `explanation`. Compatible topology is required for overlap. Constant ranks can make rank correlation undefined. |
| A comparison or export no longer has its result | Rerun the analysis after a server restart or cache eviction, then download the result again. Keep a ZIP for durable storage. |
| The browser has counts but no graph drawing | The live drawing is limited to networks of at most 80 nodes and 1,000 edges. Use graph export for larger networks. |

For a reproducible issue, include the Netbone version, Python version,
method and filter settings, and a small representative graph. Remove
sensitive data from anything you share.
