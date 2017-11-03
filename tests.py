from qir import *
import inspect


def case_1(x, z):
    y = x + 2
    if y % 2 == 0:
        z = True
    else:
        z = False
    return z


def case_2(x):
    for z in range(x, 0, -1):
        w = print(z)
    return None


def case_3(x):
    y = 0
    while x + y < 12:
        if x % 2 == 9:
            break
        elif x % 2 == 8:
            continue
        y -= 6
    return 6


def case_4(z):
    if foo:
        return True
    else:
        return False

    return 'bla'


def case_5(x, y):
    if x or y:
        z = 1
    else:
        z = 2
    return z


def case_6(x, y, z):
    z = z + 1
    u = x < y < z
    return u


for i in range(6):
    case = globals()['case_' + str(i + 1)]
    print('==== Test case n°%d ====' % i)
    print(inspect.getsource(case))
    print()
    print(encode(case))
    print()
