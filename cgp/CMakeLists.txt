﻿# CMakeList.txt : CMake project for cgp, include source and define
# project specific logic here.
#

# Add source to this project's executable.
add_executable (CGP 
    "Main.cpp" "Main.h"
    "Cgp.cpp" "Cgp.h"
    "Chromosome.cpp" "Chromosome.h"
    "Configuration.cpp" "Configuration.h"
    "CGPStream.h" "CGPStream.cpp"
    "Stream.cpp" "Stream.h"
    "StringTemplate.h" "StringTemplate.cpp" "Dataset.h" "Dataset.cpp" "Learning.h" "Learning.cpp" "Assert.h")

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET CGP PROPERTY CXX_STANDARD 20)
endif()

find_package(OpenMP REQUIRED)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
target_link_libraries(CGP OpenMP::OpenMP_CXX)
