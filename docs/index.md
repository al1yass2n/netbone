<div class="docs-hero" markdown="1">

<div class="docs-hero-text" markdown="1">

# Netbone

Extract a smaller graph from a network, inspect why its edges or nodes were
selected, and measure what the reduction preserves.
{: .intro }

[Try the web demo](browser/sample-demo.md){ .docs-button }
[Get started in Python](start/first-backbone.md){ .docs-button .docs-button-secondary }

</div>

<figure class="docs-hero-figure">
<svg viewBox="0 0 520 214" role="img" aria-labelledby="hero-figure-title">
<title id="hero-figure-title">A network of ten nodes and twenty links, and its backbone of nine links that keeps every node connected</title>
<g>
<line class="hero-edge" x1="32" y1="46" x2="102" y2="22"/>
<line class="hero-edge" x1="102" y1="22" x2="176" y2="40"/>
<line class="hero-edge" x1="176" y1="40" x2="212" y2="110"/>
<line class="hero-edge" x1="212" y1="110" x2="172" y2="178"/>
<line class="hero-edge" x1="172" y1="178" x2="96" y2="190"/>
<line class="hero-edge" x1="96" y1="190" x2="28" y2="140"/>
<line class="hero-edge" x1="28" y1="140" x2="32" y2="46"/>
<line class="hero-edge" x1="32" y1="46" x2="82" y2="104"/>
<line class="hero-edge" x1="102" y1="22" x2="82" y2="104"/>
<line class="hero-edge" x1="102" y1="22" x2="142" y2="98"/>
<line class="hero-edge" x1="176" y1="40" x2="142" y2="98"/>
<line class="hero-edge" x1="212" y1="110" x2="142" y2="98"/>
<line class="hero-edge" x1="82" y1="104" x2="142" y2="98"/>
<line class="hero-edge" x1="82" y1="104" x2="28" y2="140"/>
<line class="hero-edge" x1="82" y1="104" x2="124" y2="150"/>
<line class="hero-edge" x1="142" y1="98" x2="124" y2="150"/>
<line class="hero-edge" x1="124" y1="150" x2="172" y2="178"/>
<line class="hero-edge" x1="124" y1="150" x2="96" y2="190"/>
<line class="hero-edge" x1="142" y1="98" x2="172" y2="178"/>
<line class="hero-edge" x1="82" y1="104" x2="96" y2="190"/>
<circle class="hero-node" cx="32" cy="46" r="5"/>
<circle class="hero-node" cx="102" cy="22" r="5"/>
<circle class="hero-node" cx="176" cy="40" r="5"/>
<circle class="hero-node" cx="212" cy="110" r="5"/>
<circle class="hero-node" cx="172" cy="178" r="5"/>
<circle class="hero-node" cx="96" cy="190" r="5"/>
<circle class="hero-node" cx="28" cy="140" r="5"/>
<circle class="hero-node" cx="82" cy="104" r="6.5"/>
<circle class="hero-node" cx="142" cy="98" r="6.5"/>
<circle class="hero-node" cx="124" cy="150" r="5"/>
</g>
<path class="hero-arrow" d="M244 107 H276 M268 99 L277 107 L268 115"/>
<g>
<line class="hero-edge" x1="316" y1="46" x2="386" y2="22" opacity=".55"/>
<line class="hero-edge" x1="386" y1="22" x2="460" y2="40" opacity=".55"/>
<line class="hero-edge" x1="460" y1="40" x2="496" y2="110" opacity=".55"/>
<line class="hero-edge" x1="496" y1="110" x2="456" y2="178" opacity=".55"/>
<line class="hero-edge" x1="456" y1="178" x2="380" y2="190" opacity=".55"/>
<line class="hero-edge" x1="380" y1="190" x2="312" y2="140" opacity=".55"/>
<line class="hero-edge" x1="312" y1="140" x2="316" y2="46" opacity=".55"/>
<line class="hero-edge" x1="386" y1="22" x2="426" y2="98" opacity=".55"/>
<line class="hero-edge" x1="366" y1="104" x2="408" y2="150" opacity=".55"/>
<line class="hero-edge" x1="426" y1="98" x2="456" y2="178" opacity=".55"/>
<line class="hero-edge" x1="366" y1="104" x2="380" y2="190" opacity=".55"/>
<line class="hero-edge hero-edge--kept" x1="316" y1="46" x2="366" y2="104"/>
<line class="hero-edge hero-edge--kept" x1="386" y1="22" x2="366" y2="104"/>
<line class="hero-edge hero-edge--kept" x1="460" y1="40" x2="426" y2="98"/>
<line class="hero-edge hero-edge--kept" x1="496" y1="110" x2="426" y2="98"/>
<line class="hero-edge hero-edge--kept" x1="366" y1="104" x2="426" y2="98"/>
<line class="hero-edge hero-edge--kept" x1="366" y1="104" x2="312" y2="140"/>
<line class="hero-edge hero-edge--kept" x1="426" y1="98" x2="408" y2="150"/>
<line class="hero-edge hero-edge--kept" x1="408" y1="150" x2="456" y2="178"/>
<line class="hero-edge hero-edge--kept" x1="408" y1="150" x2="380" y2="190"/>
<circle class="hero-node hero-node--kept" cx="316" cy="46" r="5"/>
<circle class="hero-node hero-node--kept" cx="386" cy="22" r="5"/>
<circle class="hero-node hero-node--kept" cx="460" cy="40" r="5"/>
<circle class="hero-node hero-node--kept" cx="496" cy="110" r="5"/>
<circle class="hero-node hero-node--kept" cx="456" cy="178" r="5"/>
<circle class="hero-node hero-node--kept" cx="380" cy="190" r="5"/>
<circle class="hero-node hero-node--kept" cx="312" cy="140" r="5"/>
<circle class="hero-node hero-node--kept" cx="366" cy="104" r="6.5"/>
<circle class="hero-node hero-node--kept" cx="426" cy="98" r="6.5"/>
<circle class="hero-node hero-node--kept" cx="408" cy="150" r="5"/>
</g>
</svg>
<figcaption><span>Network</span><span>Backbone</span></figcaption>
</figure>

</div>

<div class="guide-grid" markdown="1">

<section markdown="1">

<div class="guide-icon"><i class="fa-solid fa-diagram-project" aria-hidden="true"></i></div>

## Prepare a network

Load a CSV edge list, read GraphML, work with NetworkX directly, or aggregate
time-stamped interactions before scoring.

[Prepare network inputs](python/inputs.md)

</section>

<section markdown="1">

<div class="guide-icon"><i class="fa-solid fa-filter" aria-hidden="true"></i></div>

## Choose what to keep

Use a method that matches the structure you want to preserve. Apply a cutoff,
a retention budget, a significance level, or the method's built-in selection.

[Choose a method and filter](python/select.md)

</section>

<section markdown="1">

<div class="guide-icon"><i class="fa-solid fa-chart-simple" aria-hidden="true"></i></div>

## Evaluate a backbone

Compare retention and connectivity, examine overlap and rank agreement, or
sweep settings to see where the result changes.

[Compare backbones](python/compare.md) · [Sweep settings](python/sweep.md)

</section>

<section markdown="1">

<div class="guide-icon"><i class="fa-solid fa-arrow-up-from-bracket" aria-hidden="true"></i></div>

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

If you use Netbone in published work, cite the paper that introduced it.
Each [method page](reference/methods.md) also lists the papers that define
that method, so cite those for the methods you report.

Yassin, A., Haidar, A., Cherifi, H., Seba, H., & Togni, O. (2023).
*An evaluation tool for backbone extraction techniques in weighted complex
networks*. Scientific Reports, 13, Article 17000.
[doi:10.1038/s41598-023-42076-3](https://doi.org/10.1038/s41598-023-42076-3)

```bibtex
@article{yassin2023netbone,
  author = {Yassin, Ali and Haidar, Abbas and Cherifi, Hocine and Seba, Hamida and Togni, Olivier},
  title = {An evaluation tool for backbone extraction techniques in weighted complex networks},
  journal = {Scientific Reports},
  year = {2023},
  volume = {13},
  number = {1},
  pages = {17000},
  doi = {10.1038/s41598-023-42076-3}
}
```
