'''
Some common functional programming (and just useful) functions
inspired by the likes of Clojure, Haskell and LISP.

NOTE: There is a naming convension of i<func_name> returning an
iterator and <func_name> returning a collection.
'''
from collections import Container
import itertools as itools
import functools as ftools
import operator as op

# Bring in functionality from the other modules
from fmap import fmap


#############################################################
# Make some library functions available without namespacing #
#############################################################
combs_wr = itools.combinations_with_replacement
combs = itools.combinations
perms = itools.permutations
takewhile = itools.takewhile
dropwhile = itools.dropwhile
groupby = itools.groupby
cprod = itools.product
mask = itools.compress  # compress is a terrible name for this!
repeat = itools.repeat
chain = itools.chain
tee = itools.tee

# Functional built-ins also include:
# map filter lambda
reduce = ftools.reduce
partial = ftools.partial

add = op.add
sub = op.sub
mul = op.mul
div = op.truediv
floordiv = op.floordiv


####################
# Helper functions #
####################
def iscollection(x):
    '''
    Allow distinguishing between string types and "true" containers
    '''
    if isinstance(x, Container):
        if not isinstance(x, (str, bytes)):
            return True
    return False


##########################
# Higher order functions #
##########################
# TODO: Improve __doc__ and related helper functionality for these!
def zipwith(func):
    '''
    Returns a function that will combine elements of a zip using func.
    `func` must be a binary operation.
    '''
    def zipper(*iterables):
        return [reduce(func, elems) for elems in zip(*iterables)]

    return zipper


def izipwith(func):
    '''
    Returns a function that will combine elements of a zip using func.
    `func` must be a binary operation.
    '''
    def izipper(*iterables):
        for elems in zip(*iterables):
            yield reduce(func, elems)

    return izipper


def compose(f, g):
    '''Create a new function from calling f(g(*args, **kwargs))'''
    def composition(*args, **kwargs):
        return f(g(*args, **kwargs))

    doc = ('The composition of calling {} followed by {}:\n'
           '>>> {}\n"{}"\n\n>>> {}\n"{}"')
    fname = f.__name__
    fdoc = f.__doc__ if f.__doc__ else 'No docstring for {}'.format(fname)
    gname = g.__name__
    gdoc = g.__doc__ if g.__doc__ else 'No docstring for {}'.format(gname)
    composition.__doc__ = doc.format(fname, gname, fname, fdoc, gname, gdoc)

    return composition


################################################
# Reductions and functions that return a value #
################################################
def nth(n, col):
    '''
    Return the nth element of a generator
    '''
    col = iter(col)
    for k in range(n):
        try:
            element = next(col)
        except StopIteration:
            raise IndexError
    return element


def foldl(col, func=add, acc=None):
    '''
    Fold a list into a single value using a binary function.
    NOTE: This is just an alias for reduce with a reordered signature
    Python's reduce is reduce(func, col, acc) which looks wrong to me...!
    '''
    if acc is not None:
        return reduce(func, col, acc)
    else:
        return reduce(func, col)


def foldr(col, func=add, acc=None):
    '''
    Fold a list with a given binary function from the right
    NOTE: Right folds and scans will blow up for infinite generators!
    '''
    try:
        col = reversed(col)
    except TypeError:
        col = reversed(list(col))

    if acc is not None:
        return reduce(func, col, acc)
    else:
        return reduce(func, col)


def dotprod(v1, v2):
    '''
    Compute the dot product of two "vectors"
    '''
    if len(v1) != len(v2):
        raise IndexError('v1 and v2 must be the same length')

    return sum(map(mul, v1, v2))


def all_equal(iterable):
    '''
    Returns True if all the elements in the iterable are the same
    '''
    # Taken from the Itertools Recipes section in the docs
    # If everything is equal then we should only have one group
    g = groupby(iterable)
    return next(g, True) and not next(g, False)


##################################################
# Functions that return a collection or iterator #
##################################################
def take(n, col):
    '''
    Return the up to the first n items from a generator
    '''
    return list(itools.islice(col, n))


def itake(n, col):
    '''
    Return the up to the first n items from a generator
    '''
    for element in itools.islice(col, n):
        yield element


def drop(n, col):
    '''
    Drop the first n items from a collection and then return the rest
    '''
    try:
        # Allows for the same call to run against an iterator or collection
        return col[n:]
    except TypeError:
        # This is an iterator: take and discard the first n values
        for k in range(n):
            try:
                next(col)
            except StopIteration:
                return []
        return list(col)


def idrop(n, col):
    '''
    Drop the first n items from a collection and then return a generator that
    yields the rest of the elements.
    '''
    try:
        # Allows for the same call to run against an iterator or collection
        return (c for c in col[n:])
    except TypeError:
        # This is an iterator: take and discard the first n values
        for k in range(n):
            try:
                next(col)
            except StopIteration:
                return col
        return col


def scanl(col, func=add, acc=None):
    '''
    Fold a collection from the left using a binary function
    and an accumulator into a list of values
    '''
    if acc is not None:
        col = chain([acc], col)

    return list(itools.accumulate(col, func))


def iscanl(col, func=add, acc=None):
    '''
    Fold a collection from the left using a binary function
    and an accumulator into a stream of values
    '''
    if acc is not None:
        col = chain([acc], col)

    for element in itools.accumulate(col, func):
        yield element


def scanr(col, func=add, acc=None):
    '''
    Use a given accumulator value to build a list of values obtained
    by repeatedly applying acc = func(next(list), acc) from the right.

    WARNING: Right folds and scans will blow up for infinite generators!
    '''
    try:
        col = reversed(col)
    except TypeError:
        col = reversed(list(col))

    if acc is not None:
        col = chain([acc], col)

    return list(itools.accumulate(col, func))


def iscanr(col, func=add, acc=None):
    '''
    Use a given accumulator value to build a stream of values obtained
    by repeatedly applying acc = func(next(list), acc) from the right.

    WARNING: Right folds and scans will blow up for infinite generators!
    '''
    try:
        col = reversed(col)
    except TypeError:
        col = reversed(list(col))

    if acc is not None:
        col = chain([acc], col)

    for element in itools.accumulate(col, func):
        yield element


def windowed(iterable, n):
    '''
    Take successive n-tuples from an iterable using a sliding window
    '''
    # Take n copies of the iterable
    iterables = tee(iterable, n)

    # Advance each to the correct starting position
    for step, it in enumerate(iterables):
        for s in range(step):
            next(it)

    # Zip the modified iterables and build a list of the result
    # NOTE: not using zip longest as we want to stop when we reach the end
    return list(zip(*iterables))


def iwindowed(iterable, n):
    '''
    Take successive n-tuples from an iterable using a sliding window
    '''
    # Take n copies of the iterable
    iterables = tee(iterable, n)

    # Advance each to the correct starting position
    for step, it in enumerate(iterables):
        for s in range(step):
            next(it)

    # Zip the modified iterables and yield the elements as a genreator
    # NOTE: not using zip longest as we want to stop when we reach the end
    for t in zip(*iterables):
        yield t


def chunked(iterable, n, fillvalue=None):
    '''
    Split an iterable into fixed-length chunks or blocks
    '''
    it = iter(iterable)
    chunks = itools.zip_longest(*[it for _ in range(n)], fillvalue=fillvalue)
    return list(chunks)


def ichunked(iterable, n, fillvalue=None):
    '''
    Split an iterable into fixed-length chunks or blocks
    '''
    it = iter(iterable)
    chunks = itools.zip_longest(*[it for _ in range(n)], fillvalue=fillvalue)

    for chunk in chunks:
        yield chunk


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


def iflatten(col):
    '''
    Flatten an arbitrarily nested list of lists into an iterator of
    single values.
    '''
    if not iscollection(col):
        yield col
    else:
        for sub_col in col:
            if not iscollection(col):
                yield col
            else:
                yield from iflatten(sub_col)
