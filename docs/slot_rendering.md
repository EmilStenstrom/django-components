# Slot rendering

This doc serves as a primer on how component slots and fills are resolved.

## Flow

1. Imagine you have a template. Some kind of text, maybe HTML:
   ```django
   | ------
   | ---------
   | ----
   | -------
   ```

2. The template may contain some vars, tags, etc
   ```django
   | -- {{ my_var }} --
   | ---------
   | ----
   | -------
   ```

3. The template also contains some slots, etc
   ```django
   | -- {{ my_var }} --
   | ---------
   | -- {% slot "myslot" %} ---
   | -- {% endslot %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | -- {% endslot %} ---
   | -------
   ```

4. Slots may be nested
   ```django
   | -- {{ my_var }} --
   | -- ABC
   | -- {% slot "myslot" %} ---
   | ----- DEF {{ my_var }}
   | ----- {% slot "myslot_inner" %}
   | -------- GHI {{ my_var }}
   | ----- {% endslot %}
   | -- {% endslot %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | ---- JKL {{ my_var }}
   | -- {% endslot %} ---
   | -------
   ```

5. Some slots may be inside fills for other components
   ```django
   | -- {{ my_var }} --
   | -- ABC
   | -- {% slot "myslot" %}---
   | ----- DEF {{ my_var }}
   | ----- {% slot "myslot_inner" %}
   | -------- GHI {{ my_var }}
   | ----- {% endslot %}
   | -- {% endslot %} ---
   | ------
   | -- {% component "mycomp" %} ---
   | ---- {% slot "myslot" %} ---
   | ------- JKL {{ my_var }}
   | ------- {% slot "myslot_inner" %}
   | ---------- MNO {{ my_var }}
   | ------- {% endslot %}
   | ---- {% endslot %} ---
   | -- {% endcomponent %} ---
   | ----
   | -- {% slot "myslot2" %} ---
   | ---- PQR {{ my_var }}
   | -- {% endslot %} ---
   | -------
   ```

5. I want to render the slots with `{% fill %}` tag that were defined OUTSIDE of this template. How do I do that?

   1. Traverse the template to collect ALL slots
      - NOTE: I will also look inside `{% slot %}` and `{% fill %}` tags, since they are all still
      defined within the same TEMPLATE.
    
      I should end up with a list like this:
      ```txt
      - Name: "myslot"
         ID 0001
         Content:
         | ----- DEF {{ my_var }}
         | ----- {% slot "myslot_inner" %}
         | -------- GHI {{ my_var }}
         | ----- {% endslot %}
      - Name: "myslot_inner"
         ID 0002
         Content:
         | -------- GHI {{ my_var }}
      - Name: "myslot"
         ID 0003
         Content:
         | ------- JKL {{ my_var }}
         | ------- {% slot "myslot_inner" %}
         | ---------- MNO {{ my_var }}
         | ------- {% endslot %}
      - Name: "myslot_inner"
         ID 0004
         Content:
         | ---------- MNO {{ my_var }}
      - Name: "myslot2"
         ID 0005
         Content:
         | ---- PQR {{ my_var }}
      ```

   2. Note the relationships - which slot is nested in which one
    
      I should end up with a graph-like data like:
      ```txt
      - 0001: [0002]
      - 0002: []
      - 0003: [0004]
      - 0004: []
      - 0005: []
      ```

      In other words, the data tells us that slot ID `0001` is PARENT of slot `0002`.

      This is important, because, IF parent template provides slot fill for slot 0001,
      then we DON'T NEED TO render it's children, AKA slot 0002.

   3. Find roots of the slot relationships

      The data from previous step can be understood also as a collection of
      directled acyclig graphs (DAG), e.g.:

      ```txt
      0001 --> 0002
      0003 --> 0004
      0005
      ```

      So we find the roots (`0001`, `0003`, `0005`), AKA slots that are NOT nested in other slots.
      We do so by going over ALL entries from previous step. Those IDs which are NOT
      mentioned in ANY of the lists are the roots.

      Because of the nature of nested structures, there cannot be any cycles.

   4. Recursively render slots, starting from roots.      
      1. First we take each of the roots.

      2. Then we check if there is a slot fill for given slot name.

      3. If YES we replace the slot node with the fill node.
         - Note: We assume slot fills are ALREADY RENDERED!
         ```django
         | ----- {% slot "myslot_inner" %}
         | -------- GHI {{ my_var }}
         | ----- {% endslot %}
         ```
         becomes
         ```django
         | ----- Bla bla
         | -------- Some Other Content
         | ----- ...
         ```
         We don't continue further, because inner slots have been overriden!

      4. If NO, then we will replace slot nodes with their children, e.g.:
         ```django
         | ---- {% slot "myslot" %} ---
         | ------- JKL {{ my_var }}
         | ------- {% slot "myslot_inner" %}
         | ---------- MNO {{ my_var }}
         | ------- {% endslot %}
         | ---- {% endslot %} ---
         ```
         Becomes
         ```django
         | ------- JKL {{ my_var }}
         | ------- {% slot "myslot_inner" %}
         | ---------- MNO {{ my_var }}
         | ------- {% endslot %}
         ```

      5. We check if the slot includes any children `{% slot %}` tags. If YES, then continue with step 4. for them, and wait until they finish.

   5. At this point, ALL slots should be rendered and we should have something like this:
      ```django
      | -- {{ my_var }} --
      | -- ABC
      | ----- DEF {{ my_var }}
      | -------- GHI {{ my_var }}
      | ------
      | -- {% component "mycomp" %} ---
      | ------- JKL {{ my_var }}
      | ---- {% component "mycomp" %} ---
      | ---------- MNO {{ my_var }}
      | ---- {% endcomponent %} ---
      | -- {% endcomponent %} ---
      | ----
      | -- {% component "mycomp2" %} ---
      | ---- PQR {{ my_var }}
      | -- {% endcomponent %} ---
      | ----
      ```
      - NOTE: Inserting fills into {% slots %} should NOT introduce new {% slots %}, as the fills should be already rendered!

## Using the correct context in {% slot/fill %} tags

In previous section, we said that the `{% fill %}` tags should be already rendered by the time they are inserted into the `{% slot %}` tags.

This is not quite true. To help you understand, consider this complex case:

```django
| -- {% for var in [1, 2, 3] %} ---
| ---- {% component "mycomp2" %} ---
| ------ {% fill "first" %}
| ------- STU {{ my_var }}
| -------     {{ var }}
| ------ {% endfill %}
| ------ {% fill "second" %}
| -------- {% component var=var my_var=my_var %}
| ---------- VWX {{ my_var }}
| -------- {% endcomponent %}
| ------ {% endfill %}
| ---- {% endcomponent %} ---
| -- {% endfor %} ---
| -------
```

We want the forloop variables to be available inside the `{% fill %}` tags. Because of that, however, we CANNOT render the fills/slots in advance.

Instead, our solution is closer to [how Vue handles slots](https://vuejs.org/guide/components/slots.html#scoped-slots). In Vue, slots are effectively functions that accept a context variables and render some content.

While we do not wrap the logic in a function, we do PREPARE IN ADVANCE:
1. The content that should be rendered for each slot
2. The context variables from `get_context_data()`

Thus, once we reach the `{% slot %}` node, in it's `render()` method, we access the data above, and, depending on the `context_behavior` setting, include the current context or not. For more info, see `SlotNode.render()`.
