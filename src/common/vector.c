#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int *items;
    size_t length;
    size_t capacity;
} Vector;

void vector_init(Vector *vector) {
    int *items = malloc(sizeof(int) * 4);

    if (items == NULL) {
        return;
    }

    vector->items = items;
    vector->length = 0;
    vector->capacity = 4;
}

int vector_push(Vector *vector, int value)
{
    if (vector->length == vector->capacity) {
        size_t new_capacity = vector->capacity * 2;

        int *temp = realloc(
            vector->items,
            sizeof(int) * new_capacity
        );

        if (temp == NULL) {
            return 0;
        }

        vector->items = temp;
        vector->capacity = new_capacity;
    }

    vector->items[vector->length] = value;
    vector->length++;

    return 1;
}

int main(void) {
    Vector vector;

    vector_init(&vector);

    for (int i=1; i<7; i++) {
        if (vector_push(&vector, i*10)) {
            printf("success");
        }
    }
    printf("%zu, %zu", vector.length, vector.capacity);

    for (int i=0; i<vector.length; i++) {
        printf("%d", vector.items[i]);
    }

    free(vector.items);

    return 0;
}