## Pattern matching in Python as a context manager and decorator

Pattern matching is awesome. Python has tuple unpacking that can be used to
do some simple pattern matching style operations but unless you want to get
really involved with `try/except` and a lot of fiddling around, it's not
as powerful as it could be.

More importantly, when you get to that stage your code looks horrible!
To quote the great Raymond:

    "There must be a better way!"


### Enter 'with pattern_match' and '@pattern_matching'
You have a choice of using the `with patter_match(foo) as m: ...` context manager
inside normal Python code or to decorate a function definition with the
`@pattern_matching` decorator that allow you to match against all named parameters
passed to the function by handling the setup of the multi-part with statement for you.
- When using the decorator version, every function parameter gains a partner that is
  prefixed with an underscore. (`bar` and `_bar`)
- The parameter can be used as normal but the underscore version is a special match
  object that can be used for pattern matching!
  - When using the context manager, you get to set the name of the match object using
  the `as` clause of the context manager.

#### A difference in Syntax
When using their context manager, I have (so far) been unable to reliably bind new
variables at runtime. As a result, accessing the results of a match is done using
dict style lookup on the match object (see the example!).<br>
If you use the decorator however, you can access any bound pattern variables
as if they were defined where they are matched. (For details on how this works, have a
look at the source: this is _highly_ cPython specific so far but it should be possible
to extend this.

### Match objects are cool!
You can use them as ofter as you want and they can be tested against types using
`>=` or against match templates using `>>`.
- When you test using `>>`, a successful match will bind the variables used in the
  template into local scope so you can use them in the rest of your code!


#### Templates are tuples of variable names without commas:
In order to specify your match templates, you need to use a *(small)* DSL to describe
the pattern you are looking for:

`template_example = '(a b c *d (_ f) ...)'`

The full rules are given below but the 10 second summary is as follows:
- Templates are strings of tuples without commas (to reduce the line noise and save you
  some key strokes).
- A template must be a *single* string-tuple (or 'struple' if you like) but it can contain
  arbitrary nested sub-templates. (aka 'sub-struples'...)
- Within a template you specify variable names that must be valid Python variable names as
  they are going to be bound following a successful match.
  - Note that if the same name is used in multiple places, it must match the same *value*
    each time for the match to succeed as a whole.
- There are a couple of special elements that you can use that give you some more powerful
  matching potential. For those, read on!


#### Allowed values in a template and what they do
    (...):   A template must start and stop with parens.
             It may also include any number of nested sub-templates.
    <var>:   Any valid python variable name is allowed.
             These are the names that will be bound into the local scope
             on the result of a successful match.
    *<var>:  Any variable name that starts with a single * is marked as
             being greedy. It will consume all remaining elements up to
             a sub-template in the same way as Python's native tuple
             unpacking.
             NOTE: You can have a maximum of one greedy variable per
                   template or sub-template.

#### Special values and their meanings
    _:       Underscore is a special element in a pattern. It denotes a
             required position in the template that must be filled but
             the result of the match is not bound. You can have any number
             of Underscores in a template.
    ...:     Ellipsis is only valid when following a sub-template. This
             causes the sub-template to be repeated greedily to the end of
             the template, combining successful matches in a list for each
             variable.
             i.e. `((a b) ...) >> [[1, 2], [3, 4], [5, 6]]`
                  will give: `a = [1, 3, 5]`
                             `b = [2, 4, 6]`


## And now for an example!
```python
from concepts import pattern_match, pattern_matching


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
                ' the second elements are {}.'.format(m['a'], m['b'], m['c']))
        elif m >> '(x y z y x)':
            print('This one is a palindrome!')
        elif m >= list:
            print("Well...it's a list! Beyond that I'm not sure...")
        elif m == 'exactly this':
            print('Exact matches work as well!')
        else:
            print('Failed matches are silent...')


>>> Trying to match, [1, 2, 3, 4, (5, 6), (7, 8), (9, 10)]
>>> This example starts with [1, 2, 3, 4] and then has a list of pairs
    where the first elements are [5, 7, 9] and the second elements are [6, 8, 10].
>>>
>>> Trying to match, [1, 2, 3, 2, 1]
>>> This one is a palindrome!
>>>
>>> Trying to match, [1, 2, 3, 2, 42]
>>> Well...it's a list! Beyond that I'm not sure...
>>>
>>> Trying to match, exactly this
>>> Exact matches work as well!


# Alternatively, use the @pattern_matching decorator to match on the arguments to
# a function. This also gives you the pattern variables in local scope.

from concepts import pattern_matching

@pattern_matching
def foo(a):
    if _a >> '(x *y)':
        print('y is ', y)

foo([1, 2, 3, 4, 5])
>>> y is [2, 3, 4, 5]
```
