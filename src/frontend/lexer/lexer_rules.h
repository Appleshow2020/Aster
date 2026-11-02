#ifndef ASTER_LEXER_RULES_H
#define ASTER_LEXER_RULES_H

#include <stddef.h>
#include "aster/token.h"

typedef struct {
    char character;
    TokenType type;
} LexerRule;

static const LexerRule OPERATOR_RULES[] = {
    {'=', TOKEN_EQUAL},
    {'+', TOKEN_PLUS},
    {'-', TOKEN_MINUS},
    {'*', TOKEN_STAR},
    {'/', TOKEN_SLASH},
    {'%', TOKEN_PERCENT},
    {'<', TOKEN_LESS},
    {'>', TOKEN_GREATER}
};

static const LexerRule DELIMITER_RULES[] = {
    {';', TOKEN_SEMICOLON},
    {',', TOKEN_COMMA},
    {'.', TOKEN_DOT},
    {':', TOKEN_COLON},
    {'(', TOKEN_LEFT_PAREN},
    {')', TOKEN_RIGHT_PAREN},
    {'{', TOKEN_LEFT_BRACE},
    {'}', TOKEN_RIGHT_BRACE}
};

typedef struct {
    const char *text;
    size_t length;
    TokenType type;
} KeywordRule;

static const KeywordRule KEYWORD_RULES[] = {
    {"int",   3, TOKEN_INT},
    {"float", 5, TOKEN_FLOAT},
    {"bool",  4, TOKEN_BOOL},
    {"str",   3, TOKEN_STR},
    {"void",  4, TOKEN_VOID},
    {"const", 5, TOKEN_CONST},
    {"true",  4, TOKEN_TRUE},
    {"false", 5, TOKEN_FALSE},
    {"null",  4, TOKEN_NULL}
};

#endif