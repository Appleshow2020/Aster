#ifndef ASTER_AST_DEBUG_H
#define ASTER_AST_DEBUG_H

#include <stdio.h>
#include "aster/ast.h"

const char *ast_node_type_name(AstNodeType type);
void ast_dump(const AstNode *node, FILE *output);
const char *ast_literal_type_name(AstLiteralType type);
const char *ast_operator_name(TokenType type);

#endif