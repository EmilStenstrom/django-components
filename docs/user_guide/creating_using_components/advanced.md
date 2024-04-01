# Advanced

## Re-using content defined in the original slot

Certain properties of a slot can be accessed from within a 'fill' context. They are provided as attributes on a user-defined alias of the targeted slot. For instance, let's say you're filling a slot called 'body'. To access properties of this slot, alias it using the 'as' keyword to a new name -- or keep the original name. With the new slot alias, you can call `<alias>.default` to insert the default content.

```htmldjango
{% component "calendar" date="2020-06-06" %}
    {% fill "body" as "body" %}{{ body.default }}. Have a great day!{% endfill %}
{% endcomponent %}
```

Produces:

```htmldjango
<div class="calendar-component">
    <div class="header">
        Calendar header
    </div>
    <div class="body">
        Today's date is <span>2020-06-06</span>. Have a great day!
    </div>
</div>
```


## Conditional slots

_Added in version 0.26._

In certain circumstances, you may want the behavior of slot filling to depend on
whether or not a particular slot is filled.

For example, suppose we have the following component template:

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
</div>
```

By default the slot named 'subtitle' is empty. Yet when the component is used without
explicit fills, the div containing the slot is still rendered, as shown below:

```html
<div class="frontmatter-component">
    <div class="title">
        Title
    </div>
    <div class="subtitle">
    </div>
</div>
```

This may not be what you want. What if instead the outer 'subtitle' div should only
be included when the inner slot is in fact filled?

The answer is to use the `{% if_filled <name> %}` tag. Together with `{% endif_filled %}`,
these define a block whose contents will be rendered only if the component slot with
the corresponding 'name' is filled.

This is what our example looks like with an 'if_filled' tag.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if_filled "subtitle" %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% endif_filled %}
</div>
```

Just as Django's builtin 'if' tag has 'elif' and 'else' counterparts, so does 'if_filled'
include additional tags for more complex branching. These tags are 'elif_filled' and
'else_filled'. Here's what our example looks like with them.

```htmldjango
<div class="frontmatter-component">
    <div class="title">
        {% slot "title" %}Title{% endslot %}
    </div>
    {% if_filled "subtitle" %}
    <div class="subtitle">
        {% slot "subtitle" %}{# Optional subtitle #}{% endslot %}
    </div>
    {% elif_filled "title" %}
        ...
    {% else_filled %}
        ...
    {% endif_filled %}
</div>
```

Sometimes you're not interested in whether a slot is filled, but rather that it _isn't_.
To negate the meaning of 'if_filled' in this way, an optional boolean can be passed to
the 'if_filled' and 'elif_filled' tags.

In the example below we use `False` to indicate that the content should be rendered
only if the slot 'subtitle' is _not_ filled.

```htmldjango
{% if_filled subtitle False %}
<div class="subtitle">
    {% slot "subtitle" %}{% endslot %}
</div>
{% endif_filled %}
```

