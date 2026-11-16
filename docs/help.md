# Troubleshooting

## Installation and startup

| Symptom | What to check |
| --- | --- |
| Import works but `nb.pipeline` is missing | Print `netbone.__version__` and `netbone.__file__`. Activate the intended environment and [install from the current checkout](start/install.md). |
| `netbone-web` is missing | Check that the environment is active. Try `python -m netbone.webapp --help` to verify the package in that interpreter. |
| The server reports an address-in-use error | Pick a different port with `--port`, then open that port in the browser. |
| The browser cannot connect | Check that the terminal process is running and that the address and port match the startup message. |
| Isolation Forest or plotting cannot import its dependency | Install the [ml or viz extra](start/install.md#optional-tools) in the environment running Netbone. |

## Input and scoring

| Symptom | What to check |
| --- | --- |
| Duplicate edge row | For a static undirected edge list, `A,B` and `B,A` denote the same edge. Aggregate duplicate observations before loading or use the temporal loader for events. |
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
