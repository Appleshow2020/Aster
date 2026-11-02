#include <string.h>
#include <ctype.h>

#include "lexer_internal.h"
#include "lexer_rules.h"

static TokenType lexer_check_keyword(Lexer *lexer) {
    size_t length = lexer->position - lexer->start;
    for (size_t i = 0; i < sizeof(KEYWORD_RULES) / sizeof(KEYWORD_RULES[i]); i++) {
        if (length == KEYWORD_RULES[i].length &&
            memcmp(lexer->source + lexer->start,
                   KEYWORD_RULES[i].text,
                   length) == 0) {
            return KEYWORD_RULES[i].type;
        }    
    }

    return TOKEN_IDENTIFIER;
}

Token lexer_scan_number(Lexer *lexer) {
    while (isdigit((unsigned char)lexer_peek(lexer))) {
        lexer_advance(lexer);
    }

    return lexer_make_token(lexer, TOKEN_INTEGER);
}

Token lexer_scan_identifier(Lexer *lexer) {
    while (isalnum((unsigned char)lexer_peek(lexer)) ||
    (unsigned char)lexer_peek(lexer) == '_') {
        lexer_advance(lexer);
    }
    return lexer_make_token(lexer, lexer_check_keyword(lexer));
}

Token lexer_scan_operator(Lexer *lexer) {
    char c = lexer_peek(lexer);

    if (c == '=' || c == '!' || c == '<' || c == '>') {
        lexer_advance(lexer);

        if (lexer_match(lexer, '=')) {
            switch (c) {
                case '=': return lexer_make_token(lexer,TOKEN_EQUAL_EQUAL);
                case '!': return lexer_make_token(lexer, TOKEN_BANG_EQUAL);
                case '<': return lexer_make_token(lexer, TOKEN_LESS_EQUAL);
                case '>': return lexer_make_token(lexer, TOKEN_GREATER_EQUAL);
            }
        }

        if (c == '!') {
            return lexer_make_token(lexer, TOKEN_ERROR);
        }
    }

    for (size_t i = 0;
             i < sizeof(OPERATOR_RULES) / sizeof(OPERATOR_RULES[0]);
             i++) {
            if (OPERATOR_RULES[i].character == c) {
                return lexer_make_token(lexer, OPERATOR_RULES[i].type);
            }
        }

    return lexer_scan_delimiter(lexer);
}

Token lexer_scan_delimiter(Lexer *lexer)
{
    char c = lexer_advance(lexer);

    for (size_t i = 0;
         i < sizeof(DELIMITER_RULES) / sizeof(DELIMITER_RULES[0]);
         i++) {
        if (DELIMITER_RULES[i].character == c) {
            return lexer_make_token(lexer, DELIMITER_RULES[i].type);
        }
    }

    return lexer_make_token(lexer, TOKEN_ERROR);
}

