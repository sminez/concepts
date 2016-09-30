# Pattern matching in Python as a context manager and decorator

There are two ways to make use of pattern_match:
    the `pattern_match` context manager
    the `pattern_matching` decorator


### Templates are written as tuples of variable names without commas:
    template_example = '(a b c *d (_ f) ...)'

### Nested sub-templates are allowed and valid elements are as follows:
    `(...):`   A template must start and stop with parens.
               It may also include any number of nested sub-templates.
    `<var>:`   Any valid python variable name is allowed.
               These are the names that will be bound into the local scope
               on the result of a successful match.
    `*<var>:`  Any variable name that starts with a single * is marked as
               being greedy. It will consume all remaining elements up to
               a sub-template in the same way as Python's native tuple
               unpacking.
               NOTE: You can have a maximum of one greedy variable per
                     template or sub-template.
#### Special values
    `_:`       Underscore is a special element in a pattern. It denotes a
               required position in the template that must be filled but
               the result of the match is not bound. You can have any number
               of Underscores in a template.
    `...:`     Ellipsis is only valid when following a sub-template. This
               causes the sub-template to be repeated greedily to the end of
               the template, combining successful matches in a list for each
               variable.
               i.e. `((a b) ...) >> [[1, 2], [3, 4], [5, 6]]`
                    will give: `a = [1, 3, 5]`
                               `b = [2, 4, 6]`
```
from pythfun import pattern_match


examples = [
    [1, 2, 3, 4, (5, 6), (7, 8), (9, 10)],
    [1, 2, 3, 2, 1],
    [1, 2, 3, 2, 42],
    'exactly this'
]

for example in examples:
    print('\nTrying to match, {}'.format(example))

    with pattern_match(example) as m:
        if m >> '(*a (b c) ...)':
            print(
                'This example starts with {} and then has a list'
                ' of pairs where the first elements are {} and'
                ' the second elements are {}.'.format(a, b, c))
        elif m >> '(x y z y x)':
            print('This one is a palindrome!')
        elif m >= list:
            print("Well...it's a list! Beyond that I'm not sure...")
        elif m == 'exactly this':
            print('Exact matches work as well!')
        else:
            print('Failed matches are silent...')
```
