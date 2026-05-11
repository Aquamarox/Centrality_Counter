cmake_minimum_required(VERSION 3.4...3.18)
project(IndexCalculator)
add_subdirectory(pybind11)
pybind11_add_module(BI_src_cpp
        CombinationCalculator.cpp
        BIVertexCalculator.cpp
        ParallelBICalculator.cpp
        binding.cpp)

find_package(OpenMP REQUIRED)
target_link_libraries(BI_src_cpp PRIVATE OpenMP::OpenMP_CXX)

target_compile_features(BI_src_cpp PRIVATE cxx_std_17)

if(MSVC)
    target_compile_options(BI_src_cpp PRIVATE /O2 /arch:AVX2)
else()
    target_compile_options(BI_src_cpp PRIVATE -O3 -march=native)
endif()

set_target_properties(BI_src_cpp PROPERTIES
        OUTPUT_NAME "bi_graph_module"
)
