from qir import *


def get_names(min_age, max_age):
    return [u.name for u in table('users') if min_age < u.age]


print(encode(get_names))
