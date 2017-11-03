from qir import *


def get_names(min_age, max_age):
    return [{'name': u.name}
            for u in table('users')
            if min_age < u.age]


def at_least(salary):
    return [{'name': e.name}
            for e in employees
            if e.salary < salary]


print(encode(get_names))
print(encode(at_least))
