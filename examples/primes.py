'''
Some toy examples of composing pure functions involving primes.
'''
import numpy as np
import pandas as pd
from math import sqrt
from sys import getsizeof
import matplotlib.pyplot as plt
from collections import defaultdict
from concepts import takewhile, itakewhile, foldl, mul, itake, scanl


def primes():
    '''Generate an infinite stream of primes'''
    sieve = defaultdict(list)
    k = 2
    while True:
        k_factors = sieve.get(k)
        if k_factors:
            del sieve[k]
            for f in k_factors:
                sieve[f+k].append(f)
        else:
            yield k
            sieve[k ** 2] = [k]
        k += 1


def factorise(n, plist=None):
    '''factorise an integer'''
    if n == 1:
        return [1]

    factors = []
    plist = plist if plist is not None else primes()

    for p in itakewhile(lambda x: x < int(sqrt(n)) + 1, plist):
        while n % p == 0:
            factors.append(p)
            n /= p
            if n == 1:
                break
    if n != 1:
        factors.append(int(n))

    return factors


def filter_factors(func, ubound):
    # Grab all of the primes that we'll need once so we can reuse them
    plist = takewhile(lambda x: x <= ubound, primes())

    return list(map(lambda k: foldl(k, mul),
                filter(lambda l: func(l),
                    map(lambda c: factorise(c, plist), range(ubound)))))


def n_or_more_factors(n, ubound=5000):
    '''Find all integers less than ubound with at least n factors'''
    return filter_factors(lambda l: len(l) >= n, ubound)


def n_or_less_factors(n, ubound=5000):
    '''Find all integers less than ubound with less than n factors'''
    return filter_factors(lambda l: 1 < len(l) <= n, ubound)


def n_factors(n, ubound=5000):
    '''Find all integers less than ubound with n factors'''
    return filter_factors(lambda l: len(l) == n, ubound)


def debug_primes():
    '''
    Generate an infinite stream of primes and log out the size of
    the sieve as it increases
    '''
    max_sieve_size = 0
    sieve_size = 0

    sieve = defaultdict(list)
    k = 2

    while True:
        k_factors = sieve.get(k)
        if k_factors:
            del sieve[k]
            for f in k_factors:
                sieve[f+k].append(f)
            sieve_size = getsizeof(sieve)
            if sieve_size > max_sieve_size:
                max_sieve_size = sieve_size
                print('{}\tincrease: {} bytes'.format(k, max_sieve_size))
        else:
            yield k
            sieve[k ** 2] = [k]
        k += 1


def by_factors(lbound=1, ubound=100):
    plist = takewhile(lambda x: x <= ubound, primes())
    return list(map(
        lambda k: {'n': foldl(k, mul),
                   'factors': k,
                   'n_factors': len(k),
                   'n_distinct_factors': len(set(k))},
                map(lambda c: factorise(c, plist), range(lbound, ubound))))


def first_largest_distinct(n):
    '''
    Find the first number that has k distinct factors for 1 <= k <= n
    '''
    return scanl(itake(n, primes()), mul)


def get_df(lbound=1, ubound=100):
    df = pd.DataFrame(by_factors(lbound, ubound))
    df.set_index('n', inplace=True)
    return df


def plot_factors(df):
    df['n_factors'].plot(kind='line')
    df['n_distinct_factors'].plot(kind='line')
    plt.show()


def plot_by_num_factors(df, unique=False, logy=False):
    column = 'n_distinct_factors' if unique else 'n_factors'
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    for n_fact in df[column].unique():
        n_df = df[df[column] == n_fact]
        n_df['count'] = np.arange(len(n_df))
        n_df.plot(x='n', y='count', ax=ax, logy=logy,
                  label='{} factors'.format(n_fact))
    plt.show()
