#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

#include "aster/ast.h"

static void test_ast_new_node(void)
{
    AstNode *node = ast_new_node(AST_LITERAL, 10, 5);

    assert(node != NULL);
    assert(node->type == AST_LITERAL);
    assert(node->line == 10);
    assert(node->column == 5);

    free(node);
}

static void test_ast_new_node_different_types(void)
{
    AstNode *program = ast_new_node(AST_PROGRAM, 1, 1);
    AstNode *binary = ast_new_node(AST_BINARY_EXPRESSION, 3, 7);
    AstNode *list = ast_new_node(AST_LIST_LITERAL, 5, 2);

    assert(program != NULL);
    assert(binary != NULL);
    assert(list != NULL);

    assert(program->type == AST_PROGRAM);
    assert(binary->type == AST_BINARY_EXPRESSION);
    assert(list->type == AST_LIST_LITERAL);

    free(program);
    free(binary);
    free(list);
}

static void test_ast_new_node_zero_position(void)
{
    AstNode *node = ast_new_node(AST_IDENTIFIER, 0, 0);

    assert(node != NULL);
    assert(node->line == 0);
    assert(node->column == 0);

    free(node);
}


static void test_ast_free_binary(void)
{
    AstNode *parent = ast_new_node(AST_BINARY_EXPRESSION, 1, 1);
    AstNode *left = ast_new_node(AST_LITERAL, 1, 1);
    AstNode *right = ast_new_node(AST_LITERAL, 1, 5);

    assert(parent != NULL);
    assert(left != NULL);
    assert(right != NULL);

    parent->as.binary_expression.left = left;
    parent->as.binary_expression.right = right;

    ast_free_node(parent);
}

static void test_ast_free_list(void)
{
    AstNode *list = ast_new_node(AST_LIST_LITERAL, 1, 1);

    assert(list != NULL);

    list->as.list_literal.elements.items =
        malloc(sizeof(AstNode *) * 2);

    assert(list->as.list_literal.elements.items != NULL);

    list->as.list_literal.elements.length = 2;
    list->as.list_literal.elements.capacity = 2;

    list->as.list_literal.elements.items[0] =
        ast_new_node(AST_LITERAL, 1, 2);

    list->as.list_literal.elements.items[1] =
        ast_new_node(AST_LITERAL, 1, 5);

    assert(list->as.list_literal.elements.items[0] != NULL);
    assert(list->as.list_literal.elements.items[1] != NULL);

    ast_free_node(list);
}

static void test_ast_free_dict(void)
{
    AstNode *dict = ast_new_node(AST_DICT_LITERAL, 1, 1);

    assert(dict != NULL);

    dict->as.dict_literal.entries.items =
        malloc(sizeof(AstDictEntry));

    assert(dict->as.dict_literal.entries.items != NULL);

    dict->as.dict_literal.entries.length = 1;
    dict->as.dict_literal.entries.capacity = 1;

    dict->as.dict_literal.entries.items[0].key =
        ast_new_node(AST_LITERAL, 1, 2);

    dict->as.dict_literal.entries.items[0].value =
        ast_new_node(AST_LITERAL, 1, 10);

    assert(dict->as.dict_literal.entries.items[0].key != NULL);
    assert(dict->as.dict_literal.entries.items[0].value != NULL);

    ast_free_node(dict);
}

static void test_ast_free_null(void)
{
    ast_free_node(NULL);
}

int main(void)
{
    test_ast_new_node();
    test_ast_new_node_different_types();
    test_ast_new_node_zero_position();
    test_ast_free_binary();
    test_ast_free_list();
    test_ast_free_dict();
    test_ast_free_null();


    printf("All AST tests passed.\n");

    return 0;
}