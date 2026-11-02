#include <stdio.h>
#include "aster/parser.h"

void parser_init(Parser *parser, Lexer lexer) {
    parser->lexer = lexer;
    parser->current_token = (Token){TOKEN_ERROR, 0, 0, 0, 0};
    parser->previous_token = (Token){TOKEN_ERROR, 0, 0, 0, 0};
    parser->had_error = 0;

    lexer_next_token(&parser->lexer, &parser->current_token);
}

void parser_advance(Parser *parser) {
    parser->previous_token = parser->current_token;
    if (parser->current_token.type != TOKEN_EOF) {
        lexer_next_token(&parser->lexer, &parser->current_token);
    }
}

int parser_check(const Parser *parser, TokenType type) {
    return parser->current_token.type == type;
}

int parser_match(Parser *parser, TokenType type) {
    if (parser_check(parser, type)) {
        parser_advance(parser);
        return 1;
    }
    return 0;
}

int parser_consume(Parser *parser, TokenType type, const char *error_message) {
    if (parser_check(parser, type)) {
        parser_advance(parser);
        return 1;
    } else {
        parser_error_at_current(parser, error_message);
        return 0;
    }
}

void parser_error_at_current(Parser *parser, const char *message) {
    parser->had_error = 1;
    fprintf(stderr, "[line %zu, column %zu] Error at '%.*s': %s\n",
            parser->current_token.line,
            parser->current_token.column,
            (int)parser->current_token.length,
            parser->lexer.source + parser->current_token.start,
            message);
}

void parser_synchronize(Parser *parser) {
    parser->had_error = 0;
    while (parser->current_token.type != TOKEN_EOF) {
        if (parser->previous_token.type == TOKEN_SEMICOLON) {
            return;
        }

        parser_advance(parser);
    }
}

static AstNode *parse_primary(Parser *parser) {
    Token token = parser->current_token;
    AstNode *node = NULL;

    switch (token.type) {
        case TOKEN_INTEGER:
        case TOKEN_FLOAT_LITERAL:
        case TOKEN_STRING:
        case TOKEN_TRUE:
        case TOKEN_FALSE:
        case TOKEN_NULL: {
            node = ast_new_node(
                AST_LITERAL,
                token.line,
                token.column
            );

            if (!node) {
                return NULL;
            }

            switch (token.type) {
                case TOKEN_INTEGER:
                    node->as.literal.type = AST_LITERAL_INTEGER;
                    break;

                case TOKEN_FLOAT_LITERAL:
                    node->as.literal.type = AST_LITERAL_FLOAT;
                    break;

                case TOKEN_STRING:
                    node->as.literal.type = AST_LITERAL_STRING;
                    break;

                case TOKEN_TRUE:
                case TOKEN_FALSE:
                    node->as.literal.type = AST_LITERAL_BOOL;
                    break;

                case TOKEN_NULL:
                    node->as.literal.type = AST_LITERAL_NULL;
                    break;

                default:
                    ast_free_node(node);
                    return NULL;
            }

            node->as.literal.value = (AstStringRef){
                .source = parser->lexer.source,
                .start = token.start,
                .length = token.length
            };

            parser_advance(parser);
            return node;
        }

        case TOKEN_IDENTIFIER:
            node = ast_new_node(
                AST_IDENTIFIER,
                token.line,
                token.column
            );

            if (!node) {
                return NULL;
            }

            node->as.identifier = (AstStringRef){
                .source = parser->lexer.source,
                .start = token.start,
                .length = token.length
            };

            parser_advance(parser);
            return node;

        default:
            parser_error_at_current(
                parser,
                "Expected expression."
            );
            return NULL;
    }
}

static AstNode *parse_unary(Parser *parser) {
    if (parser_match(parser, TOKEN_MINUS) ||
        parser_match(parser, TOKEN_PLUS)) {

        Token operator_token = parser->previous_token;

        AstNode *operand = parse_unary(parser);
        if (!operand) {
            return NULL;
        }

        AstNode *node = ast_new_node(
            AST_UNARY_EXPRESSION,
            operator_token.line,
            operator_token.column
        );

        if (!node) {
            ast_free_node(operand);
            return NULL;
        }

        node->as.unary_expression.operator_type = operator_token.type;
        node->as.unary_expression.operand = operand;

        return node;
    }

    return parse_primary(parser);
}