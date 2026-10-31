CC = gcc

CFLAGS = -std=c17 -Wall -Wextra

TARGET = aster

SOURCES = src/cli/main.c

all:
	$(CC) $(CFLAGS) $(SOURCES) -o $(TARGET)

clean:
	rm -f $(TARGET) $(TARGET).exe