cmake_minimum_required(VERSION 3.20)

project(Aster C)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(aster
    src/cli/main.c
    src/common/vector.c
    include/aster/vector.h
)