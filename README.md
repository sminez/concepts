# fmap.py - a single dispatch version of fmap for Python3

fmap is an operation on Functors.

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

And that's all there is to it!

Python's map returns an iterator that requires you to some boiler plate to get a concrete data structure out again.<br>
This is fine (if annoying and ugly) when you know - with 100% certainty - what you are mapping over. However, if<br>
the argument you are passing to map could be one of several thing then you are in trouble...

What data structure do you build at the end?

fmap ensures that - for the defined datatypes - you get back what you put in:
```
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

# Even bytes! (also bytearrays)
fmap(times2, bytes(range(1, 6)))
>>> b'\x02\x04\x06\x08\n'

# Strings are a sequence so we can fmap over them as well
fmap(times2, "ffmap me!")
>>> 'ffmmaapp  mmee!!'

# Dicts are fiddly so there are two ways to do it: fmap over the values
fmap(times2, {str(n): n for n in range(1, 6)})
>>> {'2': 4, '1': 2, '5': 10, '3': 6, '4': 8}

# Or fmap over the keys
fmap(times2, {str(n): n for n in range(1, 6)}.items())
>>> {'33': 3, '11': 1, '44': 4, '22': 2, '55': 5}

# fmap applied to None is None...are you surprised?
fmap(times2, None)
>>>
```

If you want to use a different data type (including your own user defined classes!) all you need to do is the following:

```
from fmap import fmap, instance

def my_fmap_implementation(my_type, func):
    # define how to apply func to each element of my_type

instance(fmap, my_fmap_implementation, my_type)
```

And that's it!

You may now fmap away to your heart's content.

See the awesome and fun [LearnYouAHaskell](http://learnyouahaskell.com/functors-applicative-functors-and-monoids)
for some more details on the Haskell implementation and theory behind functors if you're into that sort of thing.
    
