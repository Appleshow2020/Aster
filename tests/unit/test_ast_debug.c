#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "aster/ast_debug.h"

static void test_ast_node_type_names(void)
{
    assert(strcmp(ast_node_type_name(AST_PROGRAM), "PROGRAM") == 0);
    assert(strcmp(ast_node_type_name(AST_BLOCK), "BLOCK") == 0);
    assert(strcmp(ast_node_type_name(AST_VARIABLE_DECLARATION),
                  "VARIABLE_DECLARATION") == 0);
    assert(strcmp(ast_node_type_name(AST_BINARY_EXPRESSION),
                  "BINARY_EXPRESSION") == 0);
    assert(strcmp(ast_node_type_name(AST_UNARY_EXPRESSION),
                  "UNARY_EXPRESSION") == 0);
    assert(strcmp(ast_node_type_name(AST_LITERAL), "LITERAL") == 0);
    assert(strcmp(ast_node_type_name(AST_IDENTIFIER), "IDENTIFIER") == 0);
    assert(strcmp(ast_node_type_name(AST_EXPRESSION_STATEMENT),
                  "EXPRESSION_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_CALL_EXPRESSION),
                  "CALL_EXPRESSION") == 0);
    assert(strcmp(ast_node_type_name(AST_RETURN_STATEMENT),
                  "RETURN_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_IF_STATEMENT), "IF_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_WHILE_STATEMENT),
                  "WHILE_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_FOR_STATEMENT), "FOR_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_FUNCTION_DECLARATION),
                  "FUNCTION_DECLARATION") == 0);
    assert(strcmp(ast_node_type_name(AST_BREAK_STATEMENT),
                  "BREAK_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_CONTINUE_STATEMENT),
                  "CONTINUE_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_MATCH_STATEMENT),
                  "MATCH_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_IMPORT_STATEMENT),
                  "IMPORT_STATEMENT") == 0);
    assert(strcmp(ast_node_type_name(AST_LIST_LITERAL), "LIST_LITERAL") == 0);
    assert(strcmp(ast_node_type_name(AST_TUPLE_LITERAL), "TUPLE_LITERAL") == 0);
    assert(strcmp(ast_node_type_name(AST_DICT_LITERAL), "DICT_LITERAL") == 0);
    assert(strcmp(ast_node_type_name(AST_SET_LITERAL), "SET_LITERAL") == 0);
}

static void test_ast_dump(void) {
    const char *source = "123";
    char buffer[256];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = malloc(sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 1;
    program->as.children.capacity = 1;

    AstNode *literal = ast_new_node(AST_LITERAL, 1, 5);
    assert(literal != NULL);

    literal->as.literal.type = AST_LITERAL_INTEGER;
    literal->as.literal.value.source = source;
    literal->as.literal.value.start = 0;
    literal->as.literal.value.length = 3;

    program->as.children.items[0] = literal;

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    assert(strstr(buffer, "PROGRAM (line=1, column=1)") != NULL);
    assert(strstr(buffer, "LITERAL (line=1, column=5)") != NULL);
    assert(strstr(buffer, "Type: INTEGER") != NULL);
    assert(strstr(buffer, "Value: 123") != NULL);

    fclose(output);
    ast_free_node(program);
}

static void test_ast_import_dump(void) {
    const char *module_source = "math";
    const char *sqrt_source = "sqrt";
    const char *alias_source = "square_root";
    const char *pi_source = "pi";
    char buffer[1024];

    AstNode *node = ast_new_node(AST_IMPORT_STATEMENT, 1, 1);
    assert(node != NULL);

    node->as.import_statement.type = AST_IMPORT_FROM;

    node->as.import_statement.module.source = module_source;
    node->as.import_statement.module.start = 0;
    node->as.import_statement.module.length = 4;

    node->as.import_statement.imports.items =
        calloc(2, sizeof(AstImportItem));
    assert(node->as.import_statement.imports.items != NULL);

    node->as.import_statement.imports.length = 2;
    node->as.import_statement.imports.capacity = 2;

    AstImportItem *first = &node->as.import_statement.imports.items[0];

    first->name.source = sqrt_source;
    first->name.start = 0;
    first->name.length = 4;
    first->has_alias = 1;
    first->alias.source = alias_source;
    first->alias.start = 0;
    first->alias.length = 11;

    AstImportItem *second = &node->as.import_statement.imports.items[1];

    second->name.source = pi_source;
    second->name.start = 0;
    second->name.length = 2;

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(node, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    assert(strstr(buffer, "IMPORT_STATEMENT") != NULL);
    assert(strstr(buffer, "Import type: from") != NULL);
    assert(strstr(buffer, "Module: math") != NULL);
    assert(strstr(buffer, "Name: sqrt") != NULL);
    assert(strstr(buffer, "Alias: square_root") != NULL);
    assert(strstr(buffer, "Name: pi") != NULL);

    fclose(output);
    ast_free_node(node);
}

static void test_ast_match_dump(void) {
    const char *subject_source = "value";
    const char *first_source = "1";
    const char *second_source = "2";
    char buffer[1024];

    AstNode *node = ast_new_node(AST_MATCH_STATEMENT, 1, 1);
    assert(node != NULL);

    node->as.match_statement.expression =
        ast_new_node(AST_IDENTIFIER, 1, 7);
    assert(node->as.match_statement.expression != NULL);

    node->as.match_statement.expression->as.identifier.source =
        subject_source;
    node->as.match_statement.expression->as.identifier.start = 0;
    node->as.match_statement.expression->as.identifier.length = 5;

    node->as.match_statement.cases.items =
        calloc(2, sizeof(AstMatchCase));
    assert(node->as.match_statement.cases.items != NULL);

    node->as.match_statement.cases.length = 2;
    node->as.match_statement.cases.capacity = 2;

    AstMatchCase *first = &node->as.match_statement.cases.items[0];

    first->pattern = ast_new_node(AST_LITERAL, 2, 5);
    assert(first->pattern != NULL);

    first->pattern->as.literal.type = AST_LITERAL_INTEGER;
    first->pattern->as.literal.value.source = first_source;
    first->pattern->as.literal.value.start = 0;
    first->pattern->as.literal.value.length = 1;

    first->body = ast_new_node(AST_BLOCK, 2, 8);
    assert(first->body != NULL);

    AstMatchCase *second = &node->as.match_statement.cases.items[1];

    second->pattern = ast_new_node(AST_LITERAL, 3, 5);
    assert(second->pattern != NULL);

    second->pattern->as.literal.type = AST_LITERAL_INTEGER;
    second->pattern->as.literal.value.source = second_source;
    second->pattern->as.literal.value.start = 0;
    second->pattern->as.literal.value.length = 1;

    second->body = ast_new_node(AST_BLOCK, 3, 8);
    assert(second->body != NULL);

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(node, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    assert(strstr(buffer, "MATCH_STATEMENT") != NULL);
    assert(strstr(buffer, "Subject:") != NULL);
    assert(strstr(buffer, "Name: value") != NULL);
    assert(strstr(buffer, "Case 0:") != NULL);
    assert(strstr(buffer, "Case 1:") != NULL);
    assert(strstr(buffer, "Value: 1") != NULL);
    assert(strstr(buffer, "Value: 2") != NULL);
    assert(strstr(buffer, "Pattern:") != NULL);
    assert(strstr(buffer, "Body:") != NULL);

    fclose(output);
    ast_free_node(node);
}

static void test_ast_dump_null(void) {
    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(NULL, output);
    ast_dump(NULL, NULL);
    
    fclose(output);
}

static void test_ast_literal_type_names(void) {
    assert(strcmp(ast_literal_type_name(AST_LITERAL_INTEGER), "INTEGER") == 0);
    assert(strcmp(ast_literal_type_name(AST_LITERAL_FLOAT), "FLOAT") == 0);
    assert(strcmp(ast_literal_type_name(AST_LITERAL_STRING), "STRING") == 0);
    assert(strcmp(ast_literal_type_name(AST_LITERAL_BOOL), "BOOL") == 0);
    assert(strcmp(ast_literal_type_name(AST_LITERAL_NULL), "NULL") == 0);

    assert(strcmp(ast_literal_type_name((AstLiteralType)-1), "UNKNOWN") == 0);
}

static void test_ast_operator_names(void) {
    assert(strcmp(ast_operator_name(TOKEN_EQUAL), "=") == 0);
    assert(strcmp(ast_operator_name(TOKEN_EQUAL_EQUAL), "==") == 0);
    assert(strcmp(ast_operator_name(TOKEN_BANG_EQUAL), "!=") == 0);
    assert(strcmp(ast_operator_name(TOKEN_PLUS), "+") == 0);
    assert(strcmp(ast_operator_name(TOKEN_MINUS), "-") == 0);
    assert(strcmp(ast_operator_name(TOKEN_STAR), "*") == 0);
    assert(strcmp(ast_operator_name(TOKEN_SLASH), "/") == 0);
    assert(strcmp(ast_operator_name(TOKEN_PERCENT), "%") == 0);
    assert(strcmp(ast_operator_name(TOKEN_LESS), "<") == 0);
    assert(strcmp(ast_operator_name(TOKEN_LESS_EQUAL), "<=") == 0);
    assert(strcmp(ast_operator_name(TOKEN_GREATER), ">") == 0);
    assert(strcmp(ast_operator_name(TOKEN_GREATER_EQUAL), ">=") == 0);

    assert(strcmp(ast_operator_name((TokenType)-1), "UNKNOWN") == 0);
}

static void test_ast_expression_dump(void) {
    const char *left_source = "10";
    const char *right_source = "20";
    const char *operand_source = "5";
    char buffer[2048];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(2, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 2;
    program->as.children.capacity = 2;

    /* Binary: 10 + 20 */
    AstNode *binary = ast_new_node(AST_BINARY_EXPRESSION, 1, 1);
    assert(binary != NULL);

    binary->as.binary_expression.left =
        ast_new_node(AST_LITERAL, 1, 1);
    binary->as.binary_expression.right =
        ast_new_node(AST_LITERAL, 1, 6);

    assert(binary->as.binary_expression.left != NULL);
    assert(binary->as.binary_expression.right != NULL);

    binary->as.binary_expression.operator_type = TOKEN_PLUS;

    binary->as.binary_expression.left->as.literal.type =
        AST_LITERAL_INTEGER;
    binary->as.binary_expression.left->as.literal.value =
        (AstStringRef){left_source, 0, 2};

    binary->as.binary_expression.right->as.literal.type =
        AST_LITERAL_INTEGER;
    binary->as.binary_expression.right->as.literal.value =
        (AstStringRef){right_source, 0, 2};

    program->as.children.items[0] = binary;

    /* Unary: -5 */
    AstNode *unary = ast_new_node(AST_UNARY_EXPRESSION, 2, 1);
    assert(unary != NULL);

    unary->as.unary_expression.operator_type = TOKEN_MINUS;
    unary->as.unary_expression.operand =
        ast_new_node(AST_LITERAL, 2, 2);

    assert(unary->as.unary_expression.operand != NULL);

    unary->as.unary_expression.operand->as.literal.type =
        AST_LITERAL_INTEGER;
    unary->as.unary_expression.operand->as.literal.value =
        (AstStringRef){operand_source, 0, 1};

    program->as.children.items[1] = unary;

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    assert(strstr(buffer, "BINARY_EXPRESSION") != NULL);
    assert(strstr(buffer, "Operator: +") != NULL);
    assert(strstr(buffer, "Left:") != NULL);
    assert(strstr(buffer, "Right:") != NULL);

    assert(strstr(buffer, "UNARY_EXPRESSION") != NULL);
    assert(strstr(buffer, "Operator: -") != NULL);
    assert(strstr(buffer, "Operand:") != NULL);

    assert(strstr(buffer, "Value: 10") != NULL);
    assert(strstr(buffer, "Value: 20") != NULL);
    assert(strstr(buffer, "Value: 5") != NULL);

    fclose(output);
    ast_free_node(program);
}

static AstNode *test_new_integer_literal(
    const char *source,
    size_t line,
    size_t column
) {
    AstNode *node = ast_new_node(AST_LITERAL, line, column);
    assert(node != NULL);

    node->as.literal.type = AST_LITERAL_INTEGER;
    node->as.literal.value = (AstStringRef){
        source,
        0,
        strlen(source)
    };

    return node;
}

static void test_ast_collection_dump(void) {
    const char *callee_source = "print";
    const char *v1 = "11";
    const char *v2 = "22";
    const char *v3 = "33";
    const char *v4 = "44";
    const char *v5 = "45";
    const char *v6 = "55";

    char buffer[4096];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(5, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 5;
    program->as.children.capacity = 5;

    /* 1. Call: print(11) */
    AstNode *call = ast_new_node(AST_CALL_EXPRESSION, 1, 1);
    assert(call != NULL);

    call->as.call.callee = ast_new_node(AST_IDENTIFIER, 1, 1);
    assert(call->as.call.callee != NULL);

    call->as.call.callee->as.identifier =
        (AstStringRef){callee_source, 0, 5};

    call->as.call.arguments.items = calloc(1, sizeof(AstNode *));
    assert(call->as.call.arguments.items != NULL);

    call->as.call.arguments.length = 1;
    call->as.call.arguments.capacity = 1;
    call->as.call.arguments.items[0] =
        test_new_integer_literal(v1, 1, 7);

    program->as.children.items[0] = call;

    /* 2. List: [22] */
    AstNode *list = ast_new_node(AST_LIST_LITERAL, 2, 1);
    assert(list != NULL);

    list->as.list_literal.elements.items =
        calloc(1, sizeof(AstNode *));
    assert(list->as.list_literal.elements.items != NULL);

    list->as.list_literal.elements.length = 1;
    list->as.list_literal.elements.capacity = 1;
    list->as.list_literal.elements.items[0] =
        test_new_integer_literal(v2, 2, 2);

    program->as.children.items[1] = list;

    /* 3. Tuple: (33,) */
    AstNode *tuple = ast_new_node(AST_TUPLE_LITERAL, 3, 1);
    assert(tuple != NULL);

    tuple->as.tuple_literal.elements.items =
        calloc(1, sizeof(AstNode *));
    assert(tuple->as.tuple_literal.elements.items != NULL);

    tuple->as.tuple_literal.elements.length = 1;
    tuple->as.tuple_literal.elements.capacity = 1;
    tuple->as.tuple_literal.elements.items[0] =
        test_new_integer_literal(v3, 3, 2);

    program->as.children.items[2] = tuple;

    /* 4. Dict: {44: 45} */
    AstNode *dict = ast_new_node(AST_DICT_LITERAL, 4, 1);
    assert(dict != NULL);

    dict->as.dict_literal.entries.items =
        calloc(1, sizeof(AstDictEntry));
    assert(dict->as.dict_literal.entries.items != NULL);

    dict->as.dict_literal.entries.length = 1;
    dict->as.dict_literal.entries.capacity = 1;

    dict->as.dict_literal.entries.items[0].key =
        test_new_integer_literal(v4, 4, 2);

    dict->as.dict_literal.entries.items[0].value =
        test_new_integer_literal(v5, 4, 6);

    program->as.children.items[3] = dict;

    /* 5. Set: {55} */
    AstNode *set = ast_new_node(AST_SET_LITERAL, 5, 1);
    assert(set != NULL);

    set->as.set_literal.elements.items =
        calloc(1, sizeof(AstNode *));
    assert(set->as.set_literal.elements.items != NULL);

    set->as.set_literal.elements.length = 1;
    set->as.set_literal.elements.capacity = 1;
    set->as.set_literal.elements.items[0] =
        test_new_integer_literal(v6, 5, 2);

    program->as.children.items[4] = set;

    /* Dump */
    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    /* Node types */
    assert(strstr(buffer, "CALL_EXPRESSION") != NULL);
    assert(strstr(buffer, "LIST_LITERAL") != NULL);
    assert(strstr(buffer, "TUPLE_LITERAL") != NULL);
    assert(strstr(buffer, "DICT_LITERAL") != NULL);
    assert(strstr(buffer, "SET_LITERAL") != NULL);

    /* Values */
    assert(strstr(buffer, "Name: print") != NULL);
    assert(strstr(buffer, "Value: 11") != NULL);
    assert(strstr(buffer, "Value: 22") != NULL);
    assert(strstr(buffer, "Value: 33") != NULL);
    assert(strstr(buffer, "Value: 44") != NULL);
    assert(strstr(buffer, "Value: 45") != NULL);
    assert(strstr(buffer, "Value: 55") != NULL);

    fclose(output);
    ast_free_node(program);
}

static void test_ast_statement_dump(void) {
    const char *variable_name = "count";
    const char *function_name = "calculate";
    const char *parameter_name = "value";
    const char *parameter_type = "int";
    const char *return_type = "int";
    const char *number = "10";

    char buffer[4096];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(6, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 6;
    program->as.children.capacity = 6;

    /* 1. Variable declaration */
    AstNode *variable =
        ast_new_node(AST_VARIABLE_DECLARATION, 1, 1);
    assert(variable != NULL);

    variable->as.variable_declaration.name =
        (AstStringRef){variable_name, 0, 5};

    variable->as.variable_declaration.is_const = 0;
    variable->as.variable_declaration.has_declared_type = 1;
    variable->as.variable_declaration.declared_type =
        (AstStringRef){parameter_type, 0, 3};

    variable->as.variable_declaration.initializer =
        test_new_integer_literal(number, 1, 15);

    program->as.children.items[0] = variable;

    /* 2. Return statement */
    AstNode *return_node =
        ast_new_node(AST_RETURN_STATEMENT, 2, 1);
    assert(return_node != NULL);

    return_node->as.return_statement.value =
        test_new_integer_literal(number, 2, 8);

    program->as.children.items[1] = return_node;

    /* 3. If statement */
    AstNode *if_node =
        ast_new_node(AST_IF_STATEMENT, 3, 1);
    assert(if_node != NULL);

    if_node->as.if_statement.condition =
        test_new_integer_literal(number, 3, 4);

    if_node->as.if_statement.then_branch =
        ast_new_node(AST_BLOCK, 3, 8);
    assert(if_node->as.if_statement.then_branch != NULL);

    if_node->as.if_statement.else_branch =
        ast_new_node(AST_BLOCK, 4, 1);
    assert(if_node->as.if_statement.else_branch != NULL);

    program->as.children.items[2] = if_node;

    /* 4. While statement */
    AstNode *while_node =
        ast_new_node(AST_WHILE_STATEMENT, 5, 1);
    assert(while_node != NULL);

    while_node->as.while_statement.condition =
        test_new_integer_literal(number, 5, 7);

    while_node->as.while_statement.body =
        ast_new_node(AST_BLOCK, 5, 11);
    assert(while_node->as.while_statement.body != NULL);

    program->as.children.items[3] = while_node;

    /* 5. For statement */
    AstNode *for_node =
        ast_new_node(AST_FOR_STATEMENT, 6, 1);
    assert(for_node != NULL);

    for_node->as.for_statement.initializer = NULL;
    for_node->as.for_statement.condition =
        test_new_integer_literal(number, 6, 10);
    for_node->as.for_statement.increment = NULL;

    for_node->as.for_statement.body =
        ast_new_node(AST_BLOCK, 6, 15);
    assert(for_node->as.for_statement.body != NULL);

    program->as.children.items[4] = for_node;

    /* 6. Function declaration */
    AstNode *function =
        ast_new_node(AST_FUNCTION_DECLARATION, 7, 1);
    assert(function != NULL);

    function->as.function_declaration.name =
        (AstStringRef){function_name, 0, 9};

    function->as.function_declaration.parameters.items =
        calloc(1, sizeof(AstParameter));
    assert(function->as.function_declaration.parameters.items != NULL);

    function->as.function_declaration.parameters.length = 1;
    function->as.function_declaration.parameters.capacity = 1;

    function->as.function_declaration.parameters.items[0].name =
        (AstStringRef){parameter_name, 0, 5};

    function->as.function_declaration.parameters.items[0].type =
        (AstStringRef){parameter_type, 0, 3};

    function->as.function_declaration.has_return_type = 1;
    function->as.function_declaration.return_type =
        (AstStringRef){return_type, 0, 3};

    function->as.function_declaration.body =
        ast_new_node(AST_BLOCK, 7, 25);
    assert(function->as.function_declaration.body != NULL);

    program->as.children.items[5] = function;

    /* Dump */
    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    /* Node types */
    assert(strstr(buffer, "VARIABLE_DECLARATION") != NULL);
    assert(strstr(buffer, "RETURN_STATEMENT") != NULL);
    assert(strstr(buffer, "IF_STATEMENT") != NULL);
    assert(strstr(buffer, "WHILE_STATEMENT") != NULL);
    assert(strstr(buffer, "FOR_STATEMENT") != NULL);
    assert(strstr(buffer, "FUNCTION_DECLARATION") != NULL);

    /* Variable */
    assert(strstr(buffer, "Name: count") != NULL);
    assert(strstr(buffer, "Declared type: int") != NULL);

    /* Function */
    assert(strstr(buffer, "calculate") != NULL);
    assert(strstr(buffer, "value") != NULL);
    assert(strstr(buffer, "Return type: int") != NULL);

    /* Child nodes */
    assert(strstr(buffer, "Condition:") != NULL);
    assert(strstr(buffer, "Initializer:") != NULL);
    assert(strstr(buffer, "Body:") != NULL);

    fclose(output);
    ast_free_node(program);
}

static void test_ast_simple_statement_dump(void) {
    char buffer[1024];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(3, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 3;
    program->as.children.capacity = 3;

    /* 1. Expression statement */
    AstNode *expression_statement =
        ast_new_node(AST_EXPRESSION_STATEMENT, 1, 1);
    assert(expression_statement != NULL);

    expression_statement->as.expression_statement.expression =
        test_new_integer_literal("42", 1, 5);

    program->as.children.items[0] = expression_statement;

    /* 2. Break statement */
    AstNode *break_statement =
        ast_new_node(AST_BREAK_STATEMENT, 2, 1);
    assert(break_statement != NULL);

    program->as.children.items[1] = break_statement;

    /* 3. Continue statement */
    AstNode *continue_statement =
        ast_new_node(AST_CONTINUE_STATEMENT, 3, 1);
    assert(continue_statement != NULL);

    program->as.children.items[2] = continue_statement;

    /* Dump */
    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);

    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    /* Node types */
    assert(strstr(buffer, "EXPRESSION_STATEMENT") != NULL);
    assert(strstr(buffer, "BREAK_STATEMENT") != NULL);
    assert(strstr(buffer, "CONTINUE_STATEMENT") != NULL);

    /* Expression */
    assert(strstr(buffer, "Value: 42") != NULL);

    fclose(output);
    ast_free_node(program);
}

static void test_ast_dump_empty_arrays(void) {
    char buffer[4096];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(6, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 6;
    program->as.children.capacity = 6;

    program->as.children.items[0] =
        ast_new_node(AST_LIST_LITERAL, 1, 1);
    program->as.children.items[1] =
        ast_new_node(AST_DICT_LITERAL, 2, 1);
    program->as.children.items[2] =
        ast_new_node(AST_FUNCTION_DECLARATION, 3, 1);
    program->as.children.items[3] =
        ast_new_node(AST_MATCH_STATEMENT, 4, 1);
    program->as.children.items[4] =
        ast_new_node(AST_IMPORT_STATEMENT, 5, 1);
    program->as.children.items[5] =
        ast_new_node(AST_CALL_EXPRESSION, 6, 1);

    for (size_t i = 0; i < 6; i++) {
        assert(program->as.children.items[i] != NULL);
    }

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);
    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    assert(strstr(buffer, "LIST_LITERAL") != NULL);
    assert(strstr(buffer, "DICT_LITERAL") != NULL);
    assert(strstr(buffer, "FUNCTION_DECLARATION") != NULL);
    assert(strstr(buffer, "MATCH_STATEMENT") != NULL);
    assert(strstr(buffer, "IMPORT_STATEMENT") != NULL);
    assert(strstr(buffer, "CALL_EXPRESSION") != NULL);

    assert(strstr(buffer, "<invalid array") == NULL);

    fclose(output);
    ast_free_node(program);
}

static void test_ast_dump_invalid_arrays(void) {
    char buffer[4096];

    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program != NULL);

    program->as.children.items = calloc(6, sizeof(AstNode *));
    assert(program->as.children.items != NULL);

    program->as.children.length = 6;
    program->as.children.capacity = 6;

    AstNode *list = ast_new_node(AST_LIST_LITERAL, 1, 1);
    AstNode *dict = ast_new_node(AST_DICT_LITERAL, 2, 1);
    AstNode *function = ast_new_node(AST_FUNCTION_DECLARATION, 3, 1);
    AstNode *match = ast_new_node(AST_MATCH_STATEMENT, 4, 1);
    AstNode *import = ast_new_node(AST_IMPORT_STATEMENT, 5, 1);
    AstNode *call = ast_new_node(AST_CALL_EXPRESSION, 6, 1);

    assert(list != NULL);
    assert(dict != NULL);
    assert(function != NULL);
    assert(match != NULL);
    assert(import != NULL);
    assert(call != NULL);

    program->as.children.items[0] = list;
    program->as.children.items[1] = dict;
    program->as.children.items[2] = function;
    program->as.children.items[3] = match;
    program->as.children.items[4] = import;
    program->as.children.items[5] = call;

    /* length > 0, items == NULL인 잘못된 배열 상태 */
    list->as.list_literal.elements.length = 1;

    dict->as.dict_literal.entries.length = 1;

    function->as.function_declaration.parameters.length = 1;

    match->as.match_statement.cases.length = 1;

    import->as.import_statement.imports.length = 1;

    call->as.call.arguments.length = 1;

    FILE *output = tmpfile();
    assert(output != NULL);

    ast_dump(program, output);

    rewind(output);
    size_t length = fread(buffer, 1, sizeof(buffer) - 1, output);
    buffer[length] = '\0';

    /* 잘못된 배열마다 오류 표시가 나와야 한다. */
    const char *marker = "<invalid array: items is NULL>";
    size_t marker_count = 0;
    const char *position = buffer;

    while ((position = strstr(position, marker)) != NULL) {
        marker_count++;
        position += strlen(marker);
    }

    assert(marker_count == 6);

    fclose(output);

    /*
     * ast_free_node()는 배열의 length만큼 순회할 수 있으므로
     * 잘못된 배열을 정상적인 빈 배열 상태로 되돌린 후 해제한다.
     */
    list->as.list_literal.elements.length = 0;
    dict->as.dict_literal.entries.length = 0;
    function->as.function_declaration.parameters.length = 0;
    match->as.match_statement.cases.length = 0;
    import->as.import_statement.imports.length = 0;
    call->as.call.arguments.length = 0;

    ast_free_node(program);
}

static void test_unknown_type(void)
{
    assert(strcmp(ast_node_type_name((AstNodeType)-1), "UNKNOWN") == 0);
}

int main(void) {
    test_ast_node_type_names();
    test_unknown_type();
    test_ast_dump();
    test_ast_import_dump();
    test_ast_match_dump();
    test_ast_dump_null();
    test_ast_literal_type_names();
    test_ast_operator_names();
    test_ast_expression_dump();
    test_ast_collection_dump();
    test_ast_statement_dump();
    test_ast_simple_statement_dump();
    test_ast_dump_empty_arrays();
    test_ast_dump_invalid_arrays();


    printf("All AST debug tests passed.\n");
    return 0;
}