#include <stdlib.h>
#include "aster/ast.h"

static void ast_free_node_array(AstNodeArray *array);
static void ast_free_dict_entry_array(AstDictEntryArray *array);
static void ast_free_parameter_array(AstParameterArray *array);
static void ast_free_match_case_array(AstMatchCaseArray *array);
static void ast_free_import_array(AstImportArray *array);

AstNode *ast_new_node(AstNodeType type, size_t line, size_t column) {
    AstNode *node = calloc(1, sizeof(AstNode));
    if (!node) {
        return NULL;
    }
    node->type = type;
    node->line = line;
    node->column = column;

    return node;
}

int ast_node_array_append(AstNodeArray *array, AstNode *node) {
    if (!array || !node) {
        return 0;
    }

    if (array->length == array->capacity) {
        size_t new_capacity = array->capacity == 0
            ? 8
            : array->capacity * 2;

        AstNode **new_items = realloc(
            array->items,
            new_capacity * sizeof(AstNode *)
        );

        if (!new_items) {
            return 0;
        }

        array->items = new_items;
        array->capacity = new_capacity;
    }

    array->items[array->length++] = node;
    return 1;
}

static void ast_free_node_array(AstNodeArray *array) {
    if (!array) {
        return;
    }
    for (size_t i = 0; i < array->length; i++) {
        ast_free_node(array->items[i]);
    }
    free(array->items);
    array->items = NULL;
    array->length = 0;
    array->capacity = 0;
}

static void ast_free_dict_entry_array(AstDictEntryArray *array) {
    if (!array) {
        return;
    }
    for (size_t i = 0; i < array->length; i++) {
        ast_free_node(array->items[i].key);
        ast_free_node(array->items[i].value);
    }
    free(array->items);
    array->items = NULL;
    array->length = 0;
    array->capacity = 0;
}


static void ast_free_parameter_array(AstParameterArray *array) {
    if (!array) {
        return;
    }

    free(array->items);
    array->items = NULL;
    array->length = 0;
    array->capacity = 0;
}

static void ast_free_match_case_array(AstMatchCaseArray *array){
    if (!array) {
        return;
    }

    for (size_t i = 0; i < array->length; i++) {
        ast_free_node(array->items[i].pattern);
        ast_free_node(array->items[i].body);
    }

    free(array->items);
    array->items = NULL;
    array->length = 0;
    array->capacity = 0;
}

static void ast_free_import_array(AstImportArray *array) {
    if (!array) {
        return;
    }

    free(array->items);

    array->items = NULL;
    array->length = 0;
    array->capacity = 0;
}

void ast_free_node(AstNode *node) {
    if (!node) {
        return;
    }
    switch (node->type) {
        case AST_BINARY_EXPRESSION:
            ast_free_node(node->as.binary_expression.left);
            ast_free_node(node->as.binary_expression.right);
            break;
        
        case AST_LIST_LITERAL:
            ast_free_node_array(&node->as.list_literal.elements);
            break;

        case AST_TUPLE_LITERAL:
            ast_free_node_array(&node->as.tuple_literal.elements);
            break;

        case AST_SET_LITERAL:
            ast_free_node_array(&node->as.set_literal.elements);
            break;
        
        case AST_DICT_LITERAL:
            ast_free_dict_entry_array(&node->as.dict_literal.entries);  
            break;
        
        case AST_CALL_EXPRESSION:
            ast_free_node(node->as.call.callee);
            ast_free_node_array(&node->as.call.arguments);
            break;

        case AST_RETURN_STATEMENT:
            ast_free_node(node->as.return_statement.value);
            break;

        case AST_IF_STATEMENT:
            ast_free_node(node->as.if_statement.condition);
            ast_free_node(node->as.if_statement.then_branch);
            ast_free_node(node->as.if_statement.else_branch);
            break;

        case AST_WHILE_STATEMENT:
            ast_free_node(node->as.while_statement.condition);
            ast_free_node(node->as.while_statement.body);
            break;

        case AST_FOR_STATEMENT:
            ast_free_node(node->as.for_statement.initializer);
            ast_free_node(node->as.for_statement.condition);
            ast_free_node(node->as.for_statement.increment);
            ast_free_node(node->as.for_statement.body);
            break;

        case AST_FUNCTION_DECLARATION:
            ast_free_node(node->as.function_declaration.body);
            ast_free_parameter_array(
                &node->as.function_declaration.parameters
            );
            break;
        
        case AST_MATCH_STATEMENT:
            ast_free_node(node->as.match_statement.expression);
            ast_free_match_case_array(&node->as.match_statement.cases);
            break;
        
        case AST_BLOCK:
        case AST_PROGRAM:
            ast_free_node_array(&node->as.children);
            break;
        
        case AST_IMPORT_STATEMENT:
            ast_free_import_array(&node->as.import_statement.imports);
            break;
        
        case AST_VARIABLE_DECLARATION:
            ast_free_node(node->as.variable_declaration.initializer);
            break;

        case AST_UNARY_EXPRESSION:
            ast_free_node(node->as.unary_expression.operand);
            break;

        case AST_EXPRESSION_STATEMENT:
            ast_free_node(node->as.expression_statement.expression);
            break;

        case AST_BREAK_STATEMENT:
        case AST_CONTINUE_STATEMENT:
        case AST_LITERAL:
        case AST_IDENTIFIER:
            break;

        default:
            break;
        
    }
    free(node);
}

