# Netbone

Extract a smaller graph from a network, inspect why its edges or nodes were
selected, and measure what the reduction preserves.
{: .intro }

[Run your first Python analysis](start/first-backbone.md){ .docs-button }
[Open the browser tutorial](browser/first-session.md){ .docs-button .docs-button-secondary }

<div class="guide-grid" markdown="1">

<section markdown="1">

## Prepare a network

Load a CSV edge list, read GraphML, work with NetworkX directly, or aggregate
time-stamped interactions before scoring.

[Prepare graph inputs](python/inputs.md)

</section>

<section markdown="1">

## Choose what to keep

Use a method that matches the structure you want to preserve. Apply a cutoff,
a retention budget, a significance level, or the method's built-in selection.

[Choose a method and filter](python/select.md)

</section>

<section markdown="1">

## Evaluate a backbone

Compare retention and connectivity, examine overlap and rank agreement, or
sweep settings to see where the result changes.

[Compare backbones](python/compare.md) · [Sweep settings](python/sweep.md)

</section>

<section markdown="1">

## Share a run

Save settings, a deterministic report, and tables. Export the original and
backbone graphs for inspection in other tools.

[Save and reproduce an analysis](python/reproduce.md)

</section>

</div>

The Python package returns NetworkX graphs and pandas tables. The local web app
uses the same analysis engine and ships with the package. If you already know
the object or method you need, go to the [Python reference](reference/pipelines.md)
or the [method catalog](reference/methods.md).

## Cite Netbone

Yassin, A., Haidar, A., Cherifi, H., Seba, H., & Togni, O. (2023).
*An evaluation tool for backbone extraction techniques in weighted complex
networks*. Scientific Reports, 13, Article 17000.
[Journal article](https://doi.org/10.1038/s41598-023-42076-3)
