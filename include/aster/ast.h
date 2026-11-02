#ifndef ASTER_AST_H
#define ASTER_AST_H

#include <stddef.h>
#include "aster/token.h"

typedef enum AstNodeType {
    AST_PROGRAM,
    AST_BLOCK,
    AST_VARIABLE_DECLARATION,
    AST_BINARY_EXPRESSION,
    AST_UNARY_EXPRESSION,
    AST_LITERAL,
    AST_IDENTIFIER,
    AST_EXPRESSION_STATEMENT,
    AST_CALL_EXPRESSION,
    AST_RETURN_STATEMENT,
    AST_IF_STATEMENT,
    AST_WHILE_STATEMENT,
    AST_FOR_STATEMENT,
    AST_FUNCTION_DECLARATION,
    AST_BREAK_STATEMENT,
    AST_CONTINUE_STATEMENT,
    AST_MATCH_STATEMENT,
    AST_IMPORT_STATEMENT,
    AST_LIST_LITERAL,
    AST_TUPLE_LITERAL,
    AST_DICT_LITERAL,
    AST_SET_LITERAL
} AstNodeType;

typedef enum AstLiteralType {
    AST_LITERAL_INTEGER,
    AST_LITERAL_FLOAT,
    AST_LITERAL_STRING,
    AST_LITERAL_BOOL,
    AST_LITERAL_NULL
} AstLiteralType;

typedef struct AstStringRef{
    const char *source;
    size_t start;
    size_t length;
} AstStringRef;

typedef struct AstNode AstNode;
typedef struct AstNodeArray {
    AstNode **items;
    size_t length;
    size_t capacity;
} AstNodeArray;

typedef struct AstLiteral {
    AstLiteralType type;
    AstStringRef value;
} AstLiteral;

typedef struct AstBinaryExpression {
    AstNode *left;
    TokenType operator_type;
    AstNode *right;
} AstBinaryExpression;

typedef struct AstUnaryExpression {
    TokenType operator_type;
    AstNode *operand;
} AstUnaryExpression;

typedef struct AstVariableDeclaration {
    AstStringRef name;
    AstStringRef declared_type;
    AstNode *initializer;
    int is_const;
    int has_declared_type;
} AstVariableDeclaration;

typedef struct AstExpressionStatement {
    AstNode *expression;
} AstExpressionStatement;

typedef struct AstCallExpression {
    AstNode *callee;
    AstNodeArray arguments;
} AstCallExpression;

typedef struct AstReturnStatement {
    AstNode *value;
} AstReturnStatement;

typedef struct AstIfStatement {
    AstNode *condition;
    AstNode *then_branch;
    AstNode *else_branch;
} AstIfStatement;

typedef struct AstWhileStatement {
    AstNode *condition;
    AstNode *body;
} AstWhileStatement;

typedef struct AstForStatement {
    AstNode *initializer;
    AstNode *condition;
    AstNode *increment;
    AstNode *body;
} AstForStatement;

typedef struct AstParameter {
    AstStringRef name;
    AstStringRef type;
} AstParameter;

typedef struct AstParameterArray {
    AstParameter *items;
    size_t length;
    size_t capacity;
} AstParameterArray;

typedef struct AstFunctionDeclaration {
    AstStringRef name;
    AstParameterArray parameters;
    AstStringRef return_type;
    int has_return_type;
    AstNode *body;
} AstFunctionDeclaration;

typedef struct AstMatchCase {
    AstNode *pattern;
    AstNode *body;
} AstMatchCase;

typedef struct AstMatchCaseArray {
    AstMatchCase *items;
    size_t length;
    size_t capacity;
} AstMatchCaseArray;

typedef struct AstMatchStatement {
    AstNode *expression;
    AstMatchCaseArray cases;
} AstMatchStatement;

typedef struct AstImportItem {
    AstStringRef name;
    AstStringRef alias;
    int has_alias;
} AstImportItem;

typedef struct AstImportArray {
    AstImportItem *items;
    size_t length;
    size_t capacity;
} AstImportArray;

typedef enum AstImportType {
    AST_IMPORT_MODULE,
    AST_IMPORT_FROM
} AstImportType;

typedef struct AstImportStatement {
    AstImportType type;
    AstStringRef module;
    AstStringRef alias;
    int has_alias;
    AstImportArray imports;
} AstImportStatement;

typedef struct AstListLiteral {
    AstNodeArray elements;
} AstListLiteral;

typedef struct AstTupleLiteral {
    AstNodeArray elements;
} AstTupleLiteral;

typedef struct AstDictEntry {
    AstNode *key;
    AstNode *value;
} AstDictEntry;

typedef struct AstDictEntryArray {
    AstDictEntry *items;
    size_t length;
    size_t capacity;
} AstDictEntryArray;

typedef struct AstDictLiteral {
    AstDictEntryArray entries;
} AstDictLiteral;

typedef struct AstSetLiteral {
    AstNodeArray elements;
} AstSetLiteral;

typedef struct AstNode {
    AstNodeType type;
    size_t line;
    size_t column;
    
    union {
        AstLiteral literal;
        AstStringRef identifier;
        AstBinaryExpression binary_expression;
        AstUnaryExpression unary_expression;
        AstCallExpression call;
        AstVariableDeclaration variable_declaration;
        AstExpressionStatement expression_statement;
        AstReturnStatement return_statement;
        AstIfStatement if_statement;
        AstWhileStatement while_statement;
        AstForStatement for_statement;
        AstFunctionDeclaration function_declaration;
        AstMatchStatement match_statement;
        AstImportStatement import_statement;
        AstListLiteral list_literal;
        AstTupleLiteral tuple_literal;
        AstDictLiteral dict_literal;
        AstSetLiteral set_literal;
        AstNodeArray children;
    } as;
} AstNode;

AstNode *ast_new_node(AstNodeType type, size_t line, size_t column);
int ast_node_array_append(AstNodeArray *array, AstNode *node);
void ast_free_node(AstNode *node);


#endif