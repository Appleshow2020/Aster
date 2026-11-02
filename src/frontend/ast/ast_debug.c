#include <stdio.h>
#include "aster/ast_debug.h"

const char *ast_node_type_name(AstNodeType type) {
    switch (type) {
        case AST_PROGRAM:                 return "PROGRAM";
        case AST_BLOCK:                   return "BLOCK";
        case AST_VARIABLE_DECLARATION:    return "VARIABLE_DECLARATION";
        case AST_BINARY_EXPRESSION:       return "BINARY_EXPRESSION";
        case AST_UNARY_EXPRESSION:        return "UNARY_EXPRESSION";
        case AST_LITERAL:                 return "LITERAL";
        case AST_IDENTIFIER:              return "IDENTIFIER";
        case AST_EXPRESSION_STATEMENT:    return "EXPRESSION_STATEMENT";
        case AST_CALL_EXPRESSION:         return "CALL_EXPRESSION";
        case AST_RETURN_STATEMENT:        return "RETURN_STATEMENT";
        case AST_IF_STATEMENT:            return "IF_STATEMENT";
        case AST_WHILE_STATEMENT:         return "WHILE_STATEMENT";
        case AST_FOR_STATEMENT:           return "FOR_STATEMENT";
        case AST_FUNCTION_DECLARATION:    return "FUNCTION_DECLARATION";
        case AST_BREAK_STATEMENT:         return "BREAK_STATEMENT";
        case AST_CONTINUE_STATEMENT:      return "CONTINUE_STATEMENT";
        case AST_MATCH_STATEMENT:         return "MATCH_STATEMENT";
        case AST_IMPORT_STATEMENT:        return "IMPORT_STATEMENT";
        case AST_LIST_LITERAL:            return "LIST_LITERAL";
        case AST_TUPLE_LITERAL:           return "TUPLE_LITERAL";
        case AST_DICT_LITERAL:            return "DICT_LITERAL";
        case AST_SET_LITERAL:             return "SET_LITERAL";
        default:                          return "UNKNOWN";
    }
}

const char *ast_operator_name(TokenType type) {
    switch (type) {
        case TOKEN_EQUAL:          return "=";
        case TOKEN_EQUAL_EQUAL:    return "==";
        case TOKEN_BANG_EQUAL:     return "!=";
        case TOKEN_PLUS:           return "+";
        case TOKEN_MINUS:          return "-";
        case TOKEN_STAR:           return "*";
        case TOKEN_SLASH:          return "/";
        case TOKEN_PERCENT:        return "%";
        case TOKEN_LESS:           return "<";
        case TOKEN_LESS_EQUAL:     return "<=";
        case TOKEN_GREATER:        return ">";
        case TOKEN_GREATER_EQUAL:  return ">=";
        default:                   return "UNKNOWN";
    }
}

static void ast_dump_indent(FILE *output, size_t depth)
{
    for (size_t i = 0; i < depth; i++) {
        fputs("    ", output);
    }
}

static void ast_dump_string_ref(FILE *output, const char *label, AstStringRef value) {
    fputs(label, output);

    if (value.source == NULL) {
        fputs("<invalid source>\n", output);
        return;
    }

    if (value.length > 0) {
        fwrite(
            value.source + value.start,
            sizeof(char),
            value.length,
            output
        );
    }

    fputc('\n', output);
}

static void ast_dump_node(
    const AstNode *node,
    FILE *output,
    size_t depth
);

static void ast_dump_node_array(
    const AstNodeArray *array,
    FILE *output,
    size_t depth
) {
    if (array == NULL) {
        ast_dump_indent(output, depth);
        fputs("<invalid array>\n", output);
        return;
    }

    if (array->length > 0 && array->items == NULL) {
        ast_dump_indent(output, depth);
        fputs("<invalid array: items is NULL>\n", output);
        return;
    }

    for (size_t i = 0; i < array->length; i++) {
        ast_dump_node(array->items[i], output, depth);
    }
}
static void ast_dump_node(
    const AstNode *node,
    FILE *output,
    size_t depth
)
{
    if (node == NULL) {
        ast_dump_indent(output, depth);
        fputs("NULL\n", output);
        return;
    }

    ast_dump_indent(output, depth);
    fprintf(
        output,
        "%s (line=%zu, column=%zu)\n",
        ast_node_type_name(node->type),
        node->line,
        node->column
    );

    switch (node->type) {
        case AST_PROGRAM:
        case AST_BLOCK:
            ast_dump_node_array(&node->as.children, output, depth + 1);
            break;

        case AST_BINARY_EXPRESSION:
            ast_dump_indent(output, depth + 1);
            fprintf(
                output,
                "Operator: %s\n",
                ast_operator_name(node->as.binary_expression.operator_type)
            );
        
            ast_dump_indent(output, depth + 1);
            fputs("Left:\n", output);
            ast_dump_node(node->as.binary_expression.left, output, depth + 2);
        
            ast_dump_indent(output, depth + 1);
            fputs("Right:\n", output);
            ast_dump_node(node->as.binary_expression.right, output, depth + 2);
            break;

        case AST_UNARY_EXPRESSION:
            ast_dump_indent(output, depth + 1);
            fprintf(
                output,
                "Operator: %s\n",
                ast_operator_name(node->as.unary_expression.operator_type)
            );
        
            ast_dump_indent(output, depth + 1);
            fputs("Operand:\n", output);
        
            ast_dump_node(
                node->as.unary_expression.operand,
                output,
                depth + 2
            );

            break;
        case AST_LITERAL:
            ast_dump_indent(output, depth + 1);
            fprintf(
                output,
                "Type: %s\n",
                ast_literal_type_name(node->as.literal.type)
            );
        
            ast_dump_indent(output, depth + 1);
            ast_dump_string_ref(
                output,
                "Value: ",
                node->as.literal.value
            );
        
            break;
        
        case AST_IDENTIFIER:
            ast_dump_indent(output, depth + 1);
            fprintf(output, "Name: ");

            if (node->as.identifier.source != NULL) {
                fprintf(
                    output,
                    "%.*s\n",
                    (int)node->as.identifier.length,
                    node->as.identifier.source + node->as.identifier.start
                );
            } else {
                fputs("<invalid source>\n", output);
            }
            break;

        case AST_VARIABLE_DECLARATION:
            ast_dump_indent(output, depth + 1);
            fputs("Name: ", output);

            if (node->as.variable_declaration.name.source != NULL) {
                fprintf(
                    output,
                    "%.*s\n",
                    (int)node->as.variable_declaration.name.length,
                    node->as.variable_declaration.name.source +
                        node->as.variable_declaration.name.start
                );
            } else {
                fputs("<invalid source>\n", output);
            }
        
            ast_dump_indent(output, depth + 1);
            fprintf(
                output,
                "Const: %s\n",
                node->as.variable_declaration.is_const ? "true" : "false"
            );
        
            ast_dump_indent(output, depth + 1);
            fputs("Declared type: ", output);
        
            if (node->as.variable_declaration.has_declared_type &&
                node->as.variable_declaration.declared_type.source != NULL) {
                fprintf(
                    output,
                    "%.*s\n",
                    (int)node->as.variable_declaration.declared_type.length,
                    node->as.variable_declaration.declared_type.source +
                        node->as.variable_declaration.declared_type.start
                );
            } else {
                fputs("<inferred>\n", output);
            }
        
            ast_dump_indent(output, depth + 1);
            fputs("Initializer:\n", output);
        
            ast_dump_node(
                node->as.variable_declaration.initializer,
                output,
                depth + 2
            );
            break;

        case AST_EXPRESSION_STATEMENT:
            ast_dump_node(
                node->as.expression_statement.expression,
                output,
                depth + 1
            );
            break;

        case AST_RETURN_STATEMENT:
            ast_dump_node(
                node->as.return_statement.value,
                output,
                depth + 1
            );
            break;

                case AST_IF_STATEMENT:
            ast_dump_indent(output, depth + 1);
            fputs("Condition:\n", output);
            ast_dump_node(
                node->as.if_statement.condition,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Then branch:\n", output);
            ast_dump_node(
                node->as.if_statement.then_branch,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Else branch:\n", output);
            ast_dump_node(
                node->as.if_statement.else_branch,
                output,
                depth + 2
            );
            break;

        case AST_WHILE_STATEMENT:
            ast_dump_indent(output, depth + 1);
            fputs("Condition:\n", output);
            ast_dump_node(
                node->as.while_statement.condition,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Body:\n", output);
            ast_dump_node(
                node->as.while_statement.body,
                output,
                depth + 2
            );
            break;

        case AST_FOR_STATEMENT:
            ast_dump_indent(output, depth + 1);
            fputs("Initializer:\n", output);
            ast_dump_node(
                node->as.for_statement.initializer,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Condition:\n", output);
            ast_dump_node(
                node->as.for_statement.condition,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Increment:\n", output);
            ast_dump_node(
                node->as.for_statement.increment,
                output,
                depth + 2
            );

            ast_dump_indent(output, depth + 1);
            fputs("Body:\n", output);
            ast_dump_node(
                node->as.for_statement.body,
                output,
                depth + 2
            );
            break;

        case AST_CALL_EXPRESSION:
            ast_dump_indent(output, depth + 1);
            fputs("Callee:\n", output);
            ast_dump_node(node->as.call.callee, output, depth + 2);

            ast_dump_indent(output, depth + 1);
            fputs("Arguments:\n", output);
            ast_dump_node_array(
                &node->as.call.arguments,
                output,
                depth + 2
            );
            break;

        case AST_LIST_LITERAL:
            ast_dump_node_array(
                &node->as.list_literal.elements,
                output,
                depth + 1
            );
            break;

        case AST_TUPLE_LITERAL:
            ast_dump_node_array(
                &node->as.tuple_literal.elements,
                output,
                depth + 1
            );
            break;

        case AST_SET_LITERAL:
            ast_dump_node_array(
                &node->as.set_literal.elements,
                output,
                depth + 1
            );
            break;

                case AST_DICT_LITERAL:
            if (node->as.dict_literal.entries.length > 0 &&
                node->as.dict_literal.entries.items == NULL) {
                ast_dump_indent(output, depth + 1);
                fputs("<invalid array: items is NULL>\n", output);
                break;
            }

            for (size_t i = 0;
                 i < node->as.dict_literal.entries.length;
                 i++) {
                ast_dump_indent(output, depth + 1);
                fprintf(output, "Entry %zu:\n", i);

                ast_dump_node(
                    node->as.dict_literal.entries.items[i].key,
                    output,
                    depth + 2
                );

                ast_dump_node(
                    node->as.dict_literal.entries.items[i].value,
                    output,
                    depth + 2
                );
            }
            break;

        case AST_FUNCTION_DECLARATION:
            ast_dump_indent(output, depth + 1);
            fputs("Name: ", output);

            if (node->as.function_declaration.name.source != NULL) {
                fprintf(
                    output,
                    "%.*s\n",
                    (int)node->as.function_declaration.name.length,
                    node->as.function_declaration.name.source +
                        node->as.function_declaration.name.start
                );
            } else {
                fputs("<invalid source>\n", output);
            }
        
            ast_dump_indent(output, depth + 1);
            fputs("Parameters:\n", output);
        
            for (size_t i = 0;
                 i < node->as.function_declaration.parameters.length;
                 i++) {
                if (node->as.function_declaration.parameters.length > 0 && node->as.function_declaration.parameters.items == NULL) {
                    ast_dump_indent(output, depth + 2);
                    fputs("<invalid array: items is NULL>\n", output);
                } else {
                    for (size_t i = 0;
                         i < node->as.function_declaration.parameters.length;
                         i++) {
                        const AstParameter *parameter =
                            &node->as.function_declaration.parameters.items[i];

                        ast_dump_indent(output, depth + 2);
                        ast_dump_string_ref(output, "Name: ", parameter->name);

                        ast_dump_indent(output, depth + 2);
                        ast_dump_string_ref(output, "Type: ", parameter->type);
                    }
                }
            }
        
            ast_dump_indent(output, depth + 1);
            fputs("Return type: ", output);
        
            if (node->as.function_declaration.has_return_type &&
                node->as.function_declaration.return_type.source != NULL) {
                fprintf(
                    output,
                    "%.*s\n",
                    (int)node->as.function_declaration.return_type.length,
                    node->as.function_declaration.return_type.source +
                        node->as.function_declaration.return_type.start
                );
            } else {
                fputs("<inferred>\n", output);
            }
        
            ast_dump_indent(output, depth + 1);
            fputs("Body:\n", output);
        
            ast_dump_node(
                node->as.function_declaration.body,
                output,
                depth + 2
            );
            break;

        case AST_MATCH_STATEMENT:
            ast_dump_indent(output, depth + 1);
            fputs("Subject:\n", output);

            ast_dump_node(
                node->as.match_statement.expression,
                output,
                depth + 2
            );
        
            for (size_t i = 0; i < node->as.match_statement.cases.length; i++) {
                if (node->as.match_statement.cases.length > 0 && node->as.match_statement.cases.items == NULL) {
                    ast_dump_indent(output, depth + 1);
                    fputs("<invalid array: items is NULL>\n", output);
                    break;
                }

                for (size_t i = 0;
                     i < node->as.match_statement.cases.length;
                     i++) {
                    const AstMatchCase *match_case =
                        &node->as.match_statement.cases.items[i];

                    ast_dump_indent(output, depth + 1);
                    fprintf(output, "Case %zu:\n", i);

                    ast_dump_indent(output, depth + 2);
                    fputs("Pattern:\n", output);
                    ast_dump_node(match_case->pattern, output, depth + 3);

                    ast_dump_indent(output, depth + 2);
                    fputs("Body:\n", output);
                    ast_dump_node(match_case->body, output, depth + 3);
                }
            }
        
            break;

        case AST_IMPORT_STATEMENT:
            ast_dump_indent(output, depth + 1);
            fprintf(
                output,
                "Import type: %s\n",
                node->as.import_statement.type == AST_IMPORT_MODULE
                    ? "module"
                    : node->as.import_statement.type == AST_IMPORT_FROM
                        ? "from"
                        : "unknown"
            );
        
            ast_dump_indent(output, depth + 1);
            ast_dump_string_ref(
                output,
                "Module: ",
                node->as.import_statement.module
            );
        
            if (node->as.import_statement.has_alias) {
                ast_dump_indent(output, depth + 1);
                ast_dump_string_ref(
                    output,
                    "Alias: ",
                    node->as.import_statement.alias
                );
            }
            
            if (node->as.import_statement.imports.length > 0 &&
                node->as.import_statement.imports.items == NULL) {
                ast_dump_indent(output, depth + 1);
                fputs("<invalid array: items is NULL>\n", output);
                break;
            }

            for (size_t i = 0; i < node->as.import_statement.imports.length; i++) {
                AstImportItem *item =
                    &node->as.import_statement.imports.items[i];
            
                ast_dump_indent(output, depth + 1);
                fprintf(output, "Import item %zu:\n", i);
            
                ast_dump_indent(output, depth + 2);
                ast_dump_string_ref(output, "Name: ", item->name);
            
                if (item->has_alias) {
                    ast_dump_indent(output, depth + 2);
                    ast_dump_string_ref(output, "Alias: ", item->alias);
                }
            }
        
            break;
        case AST_BREAK_STATEMENT:
        case AST_CONTINUE_STATEMENT:
            break;
    }
}

void ast_dump(const AstNode *node, FILE *output) {
    if (output == NULL) {
        return;
    }

    ast_dump_node(node, output, 0);
}

const char *ast_literal_type_name(AstLiteralType type) {
    switch (type) {
        case AST_LITERAL_INTEGER: return "INTEGER";
        case AST_LITERAL_FLOAT:   return "FLOAT";
        case AST_LITERAL_STRING:  return "STRING";
        case AST_LITERAL_BOOL:    return "BOOL";
        case AST_LITERAL_NULL:    return "NULL";
        default:                  return "UNKNOWN";
    }
}

