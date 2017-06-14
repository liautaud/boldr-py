/**
 * A QIR expression.
 */
union Expression {
	1: Value value,
	2: Operator operator,
	3: Identifier identifier,
	4: Lambda lambda,
	5: Application application,
	6: Conditional conditional,
	7: ListConstr list_constr,
	8: ListDestr list_destr,
	9: TupleConstr tuple_constr,
	10: TupleDestr tuple_destr,
	11: Builtin builtin,
	12: Reference reference
}

/**
 * The different types of values supported by the QIR.
 */
struct Null {}
typedef i32 Number
typedef double Double
typedef string String
typedef bool Boolean

union Value {
	1: Null null,
	2: Number number,
	3: Double double,
	4: String string,
	5: Boolean boolean,
}

/**
 * The different types of operators supported by the QIR.
 */
enum OperatorType {
	SCAN = 1,
	SELECT = 2,
	PROJECT = 3,
	SORT = 4,
	LIMIT = 5,
	GROUP = 6,
	JOIN = 7
}

struct Operator {
	1: OperatorType type,
	2: optional Expression e1,
	2: optional Expression e2,
	2: optional Expression e3
}

/**
 * The Identifier, Lambda and Application nodes from the QIR.
 */
struct Identifier {
	1: string value
}

struct Lambda {
	1: Identifier parameter,
	2: Expression body
}

struct Application {
	1: Expression function,
	2: Expression argument,
}

struct Conditional {
	1: Expression condition,
	2: Expression on_true,
	3: Expression on_false
}

/**
 * The linked lists supported by the QIR.
 */
struct ListConstr {
	1: bool is_nil,
	2: optional Expression head,
	3: optional Expression tail
}

struct ListDestr {
	1: Expression input,
	2: Expression on_nil,
	3: Expression on_cons
}

/**
 * The named tuples supported by the QIR.
 */
struct TupleConstr {
	1: bool is_nil,
	2: optional Expression key,
	2: optional Expression value,
	3: optional Expression tail
}

struct TupleDestr {
	1: Expression input,
	2: Expression key
}

/**
 * Other special nodes supported by the QIR.
 */
struct Builtin {
	1: string module,
	2: string name
}

struct Reference {
	1: string input,
	2: string identifier
}

/**
 * A remote QIR evaluation server.
 */
service Evaluator {
	/**
	 * Evaluate the given QIR expression and return the resulting expression.
	 */
	Expression evaluate(1: Expression expression)
}