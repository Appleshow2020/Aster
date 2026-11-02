#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

#include "aster/ast.h"

static void test_ast_free_binary(void)
{
    AstNode *parent = ast_new_node(AST_BINARY_EXPRESSION, 1, 1);
    AstNode *left = ast_new_node(AST_LITERAL, 1, 1);
    AstNode *right = ast_new_node(AST_LITERAL, 1, 5);

    assert(parent && left && right);

    parent->as.binary_expression.left = left;
    parent->as.binary_expression.right = right;

    ast_free_node(parent);
}

static void test_ast_free_collections(void)
{
    // List
    AstNode *list = ast_new_node(AST_LIST_LITERAL, 1, 1);
    assert(list);

    list->as.list_literal.elements.items =
        malloc(sizeof(AstNode *));

    assert(list->as.list_literal.elements.items);

    list->as.list_literal.elements.length = 1;
    list->as.list_literal.elements.capacity = 1;
    list->as.list_literal.elements.items[0] =
        ast_new_node(AST_LITERAL, 1, 2);

    assert(list->as.list_literal.elements.items[0]);
    ast_free_node(list);

    // Tuple
    AstNode *tuple = ast_new_node(AST_TUPLE_LITERAL, 1, 1);
    assert(tuple);

    tuple->as.tuple_literal.elements.items =
        malloc(sizeof(AstNode *));

    assert(tuple->as.tuple_literal.elements.items);

    tuple->as.tuple_literal.elements.length = 1;
    tuple->as.tuple_literal.elements.capacity = 1;
    tuple->as.tuple_literal.elements.items[0] =
        ast_new_node(AST_LITERAL, 1, 2);

    assert(tuple->as.tuple_literal.elements.items[0]);
    ast_free_node(tuple);

    // Set
    AstNode *set = ast_new_node(AST_SET_LITERAL, 1, 1);
    assert(set);

    set->as.set_literal.elements.items =
        malloc(sizeof(AstNode *));

    assert(set->as.set_literal.elements.items);

    set->as.set_literal.elements.length = 1;
    set->as.set_literal.elements.capacity = 1;
    set->as.set_literal.elements.items[0] =
        ast_new_node(AST_LITERAL, 1, 2);

    assert(set->as.set_literal.elements.items[0]);
    ast_free_node(set);
}

static void test_ast_free_dict(void)
{
    AstNode *dict = ast_new_node(AST_DICT_LITERAL, 1, 1);
    assert(dict);

    dict->as.dict_literal.entries.items =
        malloc(sizeof(AstDictEntry));

    assert(dict->as.dict_literal.entries.items);

    dict->as.dict_literal.entries.length = 1;
    dict->as.dict_literal.entries.capacity = 1;

    dict->as.dict_literal.entries.items[0].key =
        ast_new_node(AST_LITERAL, 1, 2);

    dict->as.dict_literal.entries.items[0].value =
        ast_new_node(AST_LITERAL, 1, 5);

    assert(dict->as.dict_literal.entries.items[0].key);
    assert(dict->as.dict_literal.entries.items[0].value);

    ast_free_node(dict);
}

static void test_ast_free_function(void)
{
    AstNode *function =
        ast_new_node(AST_FUNCTION_DECLARATION, 1, 1);

    assert(function);

    function->as.function_declaration.parameters.items =
        malloc(sizeof(AstParameter));

    assert(function->as.function_declaration.parameters.items);

    function->as.function_declaration.parameters.length = 1;
    function->as.function_declaration.parameters.capacity = 1;

    function->as.function_declaration.body =
        ast_new_node(AST_BLOCK, 2, 1);

    assert(function->as.function_declaration.body);

    ast_free_node(function);
}

static void test_ast_free_match(void)
{
    AstNode *match = ast_new_node(AST_MATCH_STATEMENT, 1, 1);
    assert(match);

    match->as.match_statement.cases.items =
        malloc(sizeof(AstMatchCase));

    assert(match->as.match_statement.cases.items);

    match->as.match_statement.cases.length = 1;
    match->as.match_statement.cases.capacity = 1;

    match->as.match_statement.cases.items[0].pattern =
        ast_new_node(AST_LITERAL, 2, 5);

    match->as.match_statement.cases.items[0].body =
        ast_new_node(AST_BLOCK, 2, 8);

    assert(match->as.match_statement.cases.items[0].pattern);
    assert(match->as.match_statement.cases.items[0].body);

    ast_free_node(match);
}

static void test_ast_free_import(void)
{
    AstNode *import = ast_new_node(AST_IMPORT_STATEMENT, 1, 1);
    assert(import);

    import->as.import_statement.imports.items =
        malloc(sizeof(AstImportItem));

    assert(import->as.import_statement.imports.items);

    import->as.import_statement.imports.length = 1;
    import->as.import_statement.imports.capacity = 1;

    ast_free_node(import);
}

static void test_ast_free_program(void)
{
    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    assert(program);

    program->as.children.items = malloc(sizeof(AstNode *));
    assert(program->as.children.items);

    program->as.children.length = 1;
    program->as.children.capacity = 1;

    program->as.children.items[0] =
        ast_new_node(AST_EXPRESSION_STATEMENT, 1, 1);

    assert(program->as.children.items[0]);

    ast_free_node(program);
}

static void test_ast_free_optional_children(void)
{
    AstNodeType types[] = {
        AST_RETURN_STATEMENT,
        AST_IF_STATEMENT,
        AST_WHILE_STATEMENT,
        AST_FOR_STATEMENT,
        AST_VARIABLE_DECLARATION,
        AST_UNARY_EXPRESSION,
        AST_EXPRESSION_STATEMENT,
        AST_CALL_EXPRESSION
    };

    size_t count = sizeof(types) / sizeof(types[0]);

    for (size_t i = 0; i < count; i++) {
        AstNode *node = ast_new_node(types[i], 1, 1);
        assert(node);

        // calloc으로 모든 자식 포인터가 NULL인 상태
        ast_free_node(node);
    }
}

static void test_ast_free_null(void)
{
    ast_free_node(NULL);
}

int main(void)
{
    test_ast_free_binary();
    test_ast_free_collections();
    test_ast_free_dict();
    test_ast_free_function();
    test_ast_free_match();
    test_ast_free_import();
    test_ast_free_program();
    test_ast_free_optional_children();
    test_ast_free_null();

    printf("All AST free tests passed.\n");

    return 0;
}