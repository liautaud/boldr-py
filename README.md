# boldr-py

*Language-integrated querying for Python 3 using the BOLDR framework.*


## About this project.

This project is the result of a 6-week internship at the LRI in Orsay, in which I was tasked with with building a Python library that would allow Python developers to write database queries using idiomatic Python constructs such as comprehensions and user-defined functions.

For instance, for this user-defined function:

```py
def at_least(salary):
    return [{'name': e.name}
            for e in employees
            if e.salary < salary]
```

This library would generate the following SQL query:

```sql
SELECT e.name
FROM employees AS e 
WHERE e.salary < {salary}
```


## How it works.

Under the hood, the `qir` module uses introspection to translate Python code into an intermediate representation -- the QIR -- at runtime. This representation is then translated into the desired query language (SQL, HiveQL, JSON, etc.) using the [BOLDR framework](https://www.lri.fr/~kn/boldr_en.html) (which is being built at the LRI).

Introspection is done through CPython's `dis` module, which allows the inspection of the bytecode of any function at runtime. This bytecode is then converted into a QIR term using a symbolic stack machine described in the paper linked below. I chose to use `dis` over `inspect` as it handles anonymous functions much better, and because, let's face it, it's quite funny trying to translate bytecode into a lambda-calculus-like representation.

Communication between the Python client and the BOLDR server is achieved using [Protocol Buffers](https://github.com/google/protobuf) and [gRPC](https://github.com/grpc/grpc).


## Futher reading.

The `share` directory contains:
- a 20-page internship report that explains the whole translation procedure in details;
- a Beamer presentation -- written in French -- that summarizes the internship.