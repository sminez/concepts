# Concepts
### LISP and Haskell inspired functional programming concepts for Python

Originally this was called **fmap** and was only an implementation of the `fmap` function for Python3. Now that I've been tinkering around some more I thought it'd be nice to collect a few things together. (For about a day it was then called `PythFun` but then I saw the error of my ways...)

- [fmap](docs/fmap_README.md): apply a function to all elements of a collection style object.
- [pattern_match](docs/pattern_match_README.md): A hybrid of Haskell's pattern matching and Clojure's destructuring.
- [dispatch](dispatch.py): single and multiple dispatch for your Python functions.
- [prelude](prelude.py): a collection of functional programming functions.

Any suggestions for improvements are welcome and if you'd like to hack away and submit a pull request for a feature then raise an issue and let me know!

I hope you enjoy!


### Some examples...
```python
def fibgen():
    '''Because EVERYONE needs a list of Fibonacci numbers...'''
    yield 1
    yield from iscanl(fibgen(), add, 2)

>>> take(20, fibgen())
[1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946]


@tcall
def fact(n, acc=1):
    '''And compute some factorials...'''
    if n == 0:
        return acc
    else:
        return fact, (n-1, acc*n)

>>> fact(99)
9332621544394415268169923885626670049071596826438162146859296389521759999322991560894146397
61565182862536979208272237582511852109168640000000000000000000000

>>> import sys

>>> sys.getrecursionlimit()
2000

>>> fact(9999)
284625968091705451890641321211986889014805140170279923079417999427...
# This one is 35656 digits long...


# From prelude.py
def cmap(func, col):
    '''
    Concat-Map: map a function that takes a value and returns a list over an
    iterable and concatenate the results
    '''
    return foldl(map(func, col))


def flatten(col):
    '''
    Flatten an arbitrarily nested list of lists into a single list.
    '''
    if not iscollection(col):
        return [col]
    else:
        return cmap(flatten, col)


>>> l = [1,2,[3,4,[5,6,7],[8,9]],[10,11,12],13]

>>> flatten(l)
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
```
