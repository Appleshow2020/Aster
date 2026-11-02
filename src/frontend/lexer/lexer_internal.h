
#ifndef ASTER_LEXER_INTERNAL_H
#define ASTER_LEXER_INTERNAL_H

#include "aster/lexer.h"

int lexer_is_at_end(Lexer *lexer);
char lexer_advance(Lexer *lexer);
char lexer_peek(Lexer *lexer);
int lexer_match(Lexer *lexer, char expected);
Token lexer_make_token(Lexer *lexer, TokenType type);
Token lexer_scan_number(Lexer *lexer);
Token lexer_scan_identifier(Lexer *lexer);
Token lexer_scan_operator(Lexer *lexer);
Token lexer_scan_delimiter(Lexer *lexer);

#endif
