#include <string.h>
#include <ctype.h>
#include <stdint.h>

#include "lexer_internal.h"
#include "lexer_rules.h"

static TokenType lexer_check_keyword(Lexer *lexer) {
    size_t length = lexer->position - lexer->start;
    for (size_t i = 0; i < sizeof(KEYWORD_RULES) / sizeof(KEYWORD_RULES[0]); i++) {
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
    int is_float = 0;

    while (isdigit((unsigned char)lexer_peek(lexer))) {
        lexer_advance(lexer);
    }
    
    if (lexer_peek(lexer) == '.' &&
        lexer->position +1 < lexer->length &&
        isdigit((unsigned char)lexer->source[lexer->position + 1])) {
        lexer_advance(lexer); // Consume the '.'
        while (isdigit((unsigned char)lexer_peek(lexer))) {
            lexer_advance(lexer);
        }
        is_float = 1;
    }

    if (lexer_peek(lexer) == 'e' || lexer_peek(lexer) == 'E') {
        lexer_advance(lexer);

        if (lexer_peek(lexer) == '+' || lexer_peek(lexer) == '-') {
            lexer_advance(lexer);
        }

        if (!isdigit((unsigned char)lexer_peek(lexer))) {
            return lexer_make_token(lexer, TOKEN_ERROR);
        }
    
        while (isdigit((unsigned char)lexer_peek(lexer))) {
            lexer_advance(lexer);
        }
        
        is_float = 1;
    }

    return lexer_make_token(
        lexer, is_float ? TOKEN_FLOAT_LITERAL : TOKEN_INTEGER
    );
}

Token lexer_scan_identifier(Lexer *lexer) {
    while (isalnum((unsigned char)lexer_peek(lexer)) ||
    (unsigned char)lexer_peek(lexer) == '_') {
        lexer_advance(lexer);
    }
    return lexer_make_token(lexer, lexer_check_keyword(lexer));
}

Token lexer_scan_operator(Lexer *lexer)
{
    char c = lexer_peek(lexer);

    // Comparison operators
    if (c == '=' || c == '!' || c == '<' || c == '>') {
        lexer_advance(lexer);

        if (lexer_match(lexer, '=')) {
            switch (c) {
                case '=': return lexer_make_token(lexer, TOKEN_EQUAL_EQUAL);
                case '!': return lexer_make_token(lexer, TOKEN_BANG_EQUAL);
                case '<': return lexer_make_token(lexer, TOKEN_LESS_EQUAL);
                case '>': return lexer_make_token(lexer, TOKEN_GREATER_EQUAL);
            }
        }

        switch (c) {
            case '=': return lexer_make_token(lexer, TOKEN_EQUAL);
            case '<': return lexer_make_token(lexer, TOKEN_LESS);
            case '>': return lexer_make_token(lexer, TOKEN_GREATER);
            case '!': return lexer_make_token(lexer, TOKEN_ERROR);
        }
    }

    // Arithmetic operators
    if (c == '+' || c == '-' || c == '*' || c == '/' || c == '%') {
        lexer_advance(lexer);

        switch (c) {
            case '+': return lexer_make_token(lexer, TOKEN_PLUS);
            case '-': return lexer_make_token(lexer, TOKEN_MINUS);
            case '*': return lexer_make_token(lexer, TOKEN_STAR);
            case '/': return lexer_make_token(lexer, TOKEN_SLASH);
            case '%': return lexer_make_token(lexer, TOKEN_PERCENT);
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

static int lexer_is_hex_digit(char c)
{
    return (c >= '0' && c <= '9') ||
           (c >= 'a' && c <= 'f') ||
           (c >= 'A' && c <= 'F');
}

static int lexer_scan_hex_escape(Lexer *lexer, size_t digit_count,
                                 int validate_unicode)
{
    uint32_t value = 0;

    for (size_t i = 0; i < digit_count; i++) {
        char c = lexer_peek(lexer);

        if (!lexer_is_hex_digit(c)) {
            return 0;
        }

        lexer_advance(lexer);

        if (c >= '0' && c <= '9') {
            value = value * 16 + (uint32_t)(c - '0');
        } else if (c >= 'a' && c <= 'f') {
            value = value * 16 + (uint32_t)(c - 'a' + 10);
        } else {
            value = value * 16 + (uint32_t)(c - 'A' + 10);
        }
    }

    if (validate_unicode) {
        if (value > 0x10FFFF ||
            (value >= 0xD800 && value <= 0xDFFF)) {
            return 0;
        }
    }

    return 1;
}

int lexer_scan_escape(Lexer *lexer)
{
    char c = lexer_peek(lexer);
    if (c == '\n' || c == '\r') {
        lexer_advance(lexer);
        return 1;
    }

    if (c >= '0' && c <= '7') {
        int count = 0;
        while (count < 3) {
            c = lexer_peek(lexer);
            if (c < '0' || c > '7') {
                break;
            }
            lexer_advance(lexer);
            count++;
        }
        return 1;
    }

    switch (c) {
        case '\\':
        case '\'':
        case '"':
        case 'a':
        case 'b':
        case 'f':
        case 'n':
        case 'r':
        case 't':
        case 'v':
            lexer_advance(lexer);
            return 1;

        case 'x':
            lexer_advance(lexer);
            return lexer_scan_hex_escape(lexer, 2, 0);

        case 'u':
            lexer_advance(lexer);
            return lexer_scan_hex_escape(lexer, 4, 1);

        case 'U':
            lexer_advance(lexer);
            return lexer_scan_hex_escape(lexer, 8, 1);

        default:
            lexer_advance(lexer);
            return 0;
    }
}

Token lexer_scan_string(Lexer *lexer)
{
    lexer_advance(lexer); // Consume opening quote

    while (lexer_peek(lexer) != '"' && !lexer_is_at_end(lexer)) {
        if (lexer_peek(lexer) == '\\') {
            lexer_advance(lexer); // Consume backslash

            if (lexer_is_at_end(lexer)) {
                return lexer_make_token(lexer, TOKEN_ERROR);
            }

            if (!lexer_scan_escape(lexer)) {
                return lexer_make_token(lexer, TOKEN_ERROR);
            }
        } else {
            lexer_advance(lexer);
        }
    }

    if (lexer_is_at_end(lexer)) {
        return lexer_make_token(lexer, TOKEN_ERROR);
    }

    lexer_advance(lexer); // Consume closing quote

    return lexer_make_token(lexer, TOKEN_STRING);
}