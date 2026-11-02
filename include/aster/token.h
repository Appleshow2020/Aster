
#ifndef ASTER_TOKEN_H
#define ASTER_TOKEN_H

#include <stddef.h>

typedef enum {
    // Special
    TOKEN_EOF,
    TOKEN_ERROR,

    // Keywords ( types )
    TOKEN_INT,
    TOKEN_FLOAT,
    TOKEN_BOOL,
    TOKEN_STR,
    TOKEN_VOID,
    TOKEN_CONST,
    TOKEN_TRUE,
    TOKEN_FALSE,
    TOKEN_NULL,

    // Literals
    TOKEN_IDENTIFIER,
    TOKEN_INTEGER,

    // Operators
    TOKEN_EQUAL,           // =
    TOKEN_EQUAL_EQUAL,     // ==
    TOKEN_BANG_EQUAL,      // !=

    TOKEN_PLUS,            // +
    TOKEN_MINUS,           // -
    TOKEN_STAR,            // *
    TOKEN_SLASH,           // /
    TOKEN_PERCENT,         // %

    TOKEN_LESS,            // <
    TOKEN_LESS_EQUAL,      // <=
    TOKEN_GREATER,         // >
    TOKEN_GREATER_EQUAL,   // >=

    // Parentheses
    TOKEN_LEFT_PAREN,      // (
    TOKEN_RIGHT_PAREN,     // )
    TOKEN_LEFT_BRACE,      // {
    TOKEN_RIGHT_BRACE,     // }

    // Delimiters
    TOKEN_SEMICOLON,       // ;
    TOKEN_COMMA,           // ,
    TOKEN_DOT,             // .
    TOKEN_COLON            // :
} TokenType;

typedef struct {
    TokenType type;

    size_t start;
    size_t length;

    size_t line;
    size_t column;
} Token;

#endif
