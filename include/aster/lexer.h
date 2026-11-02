#ifndef ASTER_LEXER_H
#define ASTER_LEXER_H

#include <stddef.h>
#include "aster/token.h"

typedef struct Lexer {
    const char *source;
    size_t length;
    size_t position;
    size_t start;
    size_t line;
    size_t column;
    size_t start_line;
    size_t start_column;
} Lexer;

void lexer_init(Lexer *lexer, const char *source);
void lexer_print_error(const Lexer *lexer, const Token *token);
Token lexer_next_token(Lexer *lexer);
Token lexer_scan_number(Lexer *lexer);
Token lexer_scan_identifier(Lexer *lexer);
Token lexer_scan_operator(Lexer *lexer);
Token lexer_scan_delimiter(Lexer *lexer);

#endif