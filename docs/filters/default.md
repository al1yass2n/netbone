# Default Filter

`default` resolves to the filter declared by a method's metadata.

## Summary

- **Name:** `default`
- **Input:** `MethodResult`
- **Output:** `Selection`
- **Behavior:** delegates to the method's `default_filter`

## Behavior

When a method defines a default filter, `default` applies that filter with any
method-declared default parameters plus parameters passed by the user. User
parameters override method defaults.

For example, `disparity` declares `significance` as its default filter:

```python
result = (
    nb.pipeline()
    .score("disparity", weight="weight")
    .filter("default", alpha=0.05)
    .run(graph)
)
```

The resulting `Selection` records the resolved strategy, such as
`"significance"`.

`link_salience` declares a threshold default:

```python
result = (
    nb.pipeline().score("link_salience", weight="weight").filter("default").run(graph)
)
```

This resolves to a threshold filter on `link_salience` with `value=0.5` and
`operator="greater_equal"`.

User parameters are passed through to the resolved filter. For
`link_prediction`, the default retained fraction is `0.1`, but the user must
state the ranking direction:

```python
result = (
    nb.pipeline()
    .score("link_prediction", similarity="shortest_path")
    .filter("default", direction="lower")
    .run(graph)
)
```

## Validation

The filter raises `ConfigurationError` when the method does not define a
default filter or when the resolved default filter is missing required
parameters.
