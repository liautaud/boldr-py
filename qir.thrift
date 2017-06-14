/**
 * A QIR expression.
 */
union Expression {
	1: Value e_value,
	2: Operator e_operator,
	3: Identifier e_identifier,
	4: Lambda e_lambda,
	5: Application e_application,
	6: Conditional e_conditional,
	7: ListConstr e_list_constr,
	8: ListDestr e_list_destr,
	9: TupleConstr e_tuple_constr,
	10: TupleDestr e_tuple_destr,
	11: Builtin e_builtin,
	12: Reference e_reference
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
	1: Null v_null,
	2: Number v_number,
	3: Double v_double,
	4: String v_string,
	5: Boolean v_boolean,
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
	1: OperatorType o_type,
	2: optional Expression o_first,
	3: optional Expression o_second,
	4: optional Expression o_third
}

/**
 * The Identifier, Lambda and Application nodes from the QIR.
 */
struct Identifier {
	1: string i_value
}

struct Lambda {
	1: Identifier l_parameter,
	2: Expression l_body
}

struct Application {
	1: Expression a_function,
	2: Expression a_argument,
}

struct Conditional {
	1: Expression c_condition,
	2: Expression c_on_true,
	3: Expression c_on_false
}

/**
 * The linked lists supported by the QIR.
 */
struct ListConstr {
	1: bool lc_is_nil,
	2: optional Expression lc_head,
	3: optional Expression lc_tail
}

struct ListDestr {
	1: Expression ld_input,
	2: Expression ld_on_nil,
	3: Expression ld_on_cons
}

/**
 * The named tuples supported by the QIR.
 */
struct TupleConstr {
	1: bool tc_is_nil,
	2: optional Expression tc_key,
	3: optional Expression tc_value,
	4: optional Expression tc_tail
}

struct TupleDestr {
	1: Expression td_input,
	2: Expression td_key
}

/**
 * Other special nodes supported by the QIR.
 */
struct Builtin {
	1: string b_module,
	2: string b_name
}

struct Reference {
	1: string r_input,
	2: string r_identifier
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