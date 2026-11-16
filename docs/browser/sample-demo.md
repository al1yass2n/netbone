# Try a sample network

Four researchers are linked by the papers they wrote together. Netbone scores
each link by its publication count. Move the sliders to keep different
fractions of the strongest links and compare the resulting backbones.

<div data-sample-demo class="sample-demo">

<p data-demo-status role="status" hidden>Loading the sample network…</p>

<div data-demo-view hidden>

<div class="demo-panels">
<section class="demo-panel" data-demo-panel aria-labelledby="demo-title-a">
  <h2 id="demo-title-a">Backbone A</h2>
  <div class="demo-slider-label">
    <label for="demo-fraction-a">Retained fraction for A</label>
    <output for="demo-fraction-a">25%</output>
  </div>
  <input id="demo-fraction-a" type="range" min="0" max="100" step="25" value="25">
  <canvas width="800" height="480" role="img" aria-label="Collaboration network for backbone A"></canvas>
  <p class="demo-count" data-demo-count></p>
</section>
<section class="demo-panel" data-demo-panel aria-labelledby="demo-title-b">
  <h2 id="demo-title-b">Backbone B</h2>
  <div class="demo-slider-label">
    <label for="demo-fraction-b">Retained fraction for B</label>
    <output for="demo-fraction-b">75%</output>
  </div>
  <input id="demo-fraction-b" type="range" min="0" max="100" step="25" value="75">
  <canvas width="800" height="480" role="img" aria-label="Collaboration network for backbone B"></canvas>
  <p class="demo-count" data-demo-count></p>
</section>
</div>

<p class="demo-legend">Thick teal lines show retained links. Thin gray lines show removed links.</p>
<p class="demo-comparison" data-demo-comparison role="status"></p>

<table class="demo-table">
  <caption>Link weights and selections</caption>
  <thead>
    <tr><th scope="col">Researchers</th><th scope="col">Joint papers</th><th scope="col">A</th><th scope="col">B</th></tr>
  </thead>
  <tbody data-demo-links></tbody>
</table>

</div>

<noscript><p>Enable JavaScript to explore the sample network.</p></noscript>

</div>

The two views use the same layout so you can compare links directly.
**Edge Jaccard** is the share of links that both backbones keep, among all
links kept by either backbone. The demo uses results precomputed with Netbone.

[Analyze your own network in the local app](launch.md){ .docs-button }
