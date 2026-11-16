# Method default

Use `default` to apply the selection rule declared by a scoring method.
Netbone reads the method's default filter and merges in any overrides you
supply. The accepted arguments belong to the resolved filter. For example,
a method that defaults to significance accepts `alpha`, while one that
defaults to fraction accepts `fraction`.

Some structural methods report membership flags. For these methods, the
default filter extracts the marked edges directly. Others use a preset
cutoff or fraction. Inspect `nb.describe_method(name)` and the
[method catalog](../reference/methods.md) to check which rule applies.
A method without a registered default, such as Edge Weight, requires an
explicit filter. Link Prediction requires `direction` even when using
the default.

```python
result = nb.pipeline().score("maximum_spanning_forest").filter("default").run(graph)
```

Use the [sample graph](../reference/methods.md#try-a-method) for this example.
