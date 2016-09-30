# fmap.py - a single dispatch version of fmap for Python3

*While there are multiple Haskellesque 'lets put monads in Python!' style libraries out there, most don't seem to focus
on taking the nice bits of Haskell's functional approach and giving them a nice Pythonic interface.<br> `fmap.py` is a very simple take on `fmap` that lets you remove some unnecesary boiler plate when you are applying a function to each
element of a collection. I hope you like it!*


### They say fmap is an operation on Functors...
"What's a Functor?!", I hear you cry.

Well, the Haskell docs have this to say on the matter:
```
Functors:
  Uniform action over a parameterized type, generalizing the map function on lists. 
  The Functor class is used for types that can be mapped over. Instances of Functor 
  should satisfy the following laws:

    class Functor f where
        fmap id  ==  id
        fmap (f . g)  ==  fmap f . fmap g
```

Of course...thanks for that. Now I know exactly what's going on...

The important part is the second half of the first sentence: `"generalizing the map function on lists."`

### And that's all there is to it!

Python's map returns an iterator that requires you to some boiler plate to get a concrete data structure out again.<br>
This is fine (if annoying and ugly) when you know - with 100% certainty - what you are mapping over. However, if<br>
the argument you are passing to map could be one of several thing then you are in trouble...

What data structure do you build at the end?

### fmap ensures that - for the defined datatypes - you get back what you put in:
```python
def times2(x):
    return x * 2

# With a list this looks exactly the same as the less pleasing list(map(times2, [1,2,3,4,5]))
fmap(times2, [1,2,3,4,5])
>>> [2, 4, 6, 8, 10]

# Works for sets
fmap(times2, {1,2,3,4,5})
>>> {8, 2, 10, 4, 6}

# And tuples
fmap(times2, (1,2,3,4,5))
>>> (2, 4, 6, 8, 10)

# Strings are a sequence so we can fmap over them as well
fmap(times2, "ffmap me!")
>>> 'ffmmaapp  mmee!!'

# Even bytes! (also bytearrays)
fmap(times2, bytes(range(1, 6)))
>>> b'\x02\x04\x06\x08\n'

# Dicts are fiddly so there are some helpers.
# By default you fmap over the values:
fmap(times2, {str(n): n for n in range(1, 6)})
>>> {'2': 4, '1': 2, '5': 10, '3': 6, '4': 8}

# To fmap over the keys, wrap the function in `on_keys`:
fmap(on_keys(times2), {str(n): n for n in range(1, 6)})
>>> {'33': 3, '11': 1, '44': 4, '22': 2, '55': 5}

# Or, if the function takes two values and returns two values you can use it
# directly:
def values_are_awesome(a, b):
    return a, 'Awesome!'

fmap(values_are_awesome, {str(n): n for n in range(1, 6)})
>>> {'2': 'Awesome!', '1': 'Awesome!', '5': 'Awesome!', '3': 'Awesome!', '4': 'Awesome!'}


# Pass in an iterator, range or generator and you'll get out a new generator
fmap(times2, iter([1,2,3,4,5]))
>>> <generator object _fmap.<locals>.<genexpr> at 0x7f1511028eb8>

# fmap applied to None is None...are you surprised?
fmap(times2, None)
>>>
```

#### If you want to use a different data type (including your own user defined classes!) all you need to do is the following. We'll use a (very) simple binary tree class as our example:

```python
from concepts import fmap, fmap_for


class Btree:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self):
        return str((self.val, self.left, self.right))


@fmap_for(Btree)
def _fmap_btree(func, t):
    return Btree(func(t.val), fmap(func, t.left), fmap(func, t.right))


# Lets try it out!
>>> b = Btree(4, Btree(3, Btree(2)), Btree(1, None, Btree(0)))
>>> b
(4, (3, (2, None, None), None), (1, None, (0, None, None)))
>>> b.left
(3, (2, None, None), None)
>>> b.right
(1, None, (0, None, None))

>>> fmap(times2, b)
(8, (6, (4, None, None), None), (2, None, (0, None, None)))
```

Or if you prefer using a function instead of a decorator (which also allows you to
register pre-defined functions):

```python
from concepts import fmap, instance

instance(fmap, _fmap_btree, Btree)
```

And that's it!

You may now fmap away to your heart's content.

See the awesome and fun [LearnYouAHaskell](http://learnyouahaskell.com/functors-applicative-functors-and-monoids)
for some more details on the Haskell implementation and theory behind functors if you're into that sort of thing.


### A note on implementation
Originally this was implemented using the `functools.singledispatch` decorator but that caused a couple of issues due its use of the MRO to find implementations for subclasses. As a result, I have written a (much simpler and less powerful) version that allows you to dispatch on a chosen argument index or on the types of all arguments. This can be found in dispatch.py if you are interested.
