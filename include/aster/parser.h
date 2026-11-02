#ifndef ASTER_PARSER_H
#define ASTER_PARSER_H

#include "aster/lexer.h"
#include "aster/token.h"
#include "aster/ast.h"

typedef struct Parser {
    Lexer lexer;
    Token current_token;
    Token previous_token;
    int had_error;
} Parser;

void parser_init(Parser *parser, Lexer lexer);
void parser_advance(Parser *parser);
int parser_check(const Parser *parser, TokenType type);
int parser_match(Parser *parser, TokenType type);
int parser_consume(Parser *parser, TokenType type, const char *error_message);
void parser_error_at_current(Parser *parser, const char *message);
void parser_synchronize(Parser *parser);
static AstNode *parse_primary(Parser *parser);

#endif