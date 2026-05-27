#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "CombinationCalculator.h"
#include "ParallelBICalculator.h"

namespace py = pybind11;

PYBIND11_MODULE(bi_graph_module, m) {
    m.doc() = "Module for parallel computing Bundle Index on graphs";

    py::class_<CombinationCalculator>(m, "CombinationCalculator")
        .def(py::init<int>(), py::arg("max_n"));

    py::class_<ParallelBICalculator>(m, "ParallelBICalculator")
        .def(py::init<int, int, const CombinationCalculator&>(),
             py::arg("k"),
             py::arg("num_threads"),
             py::arg("comb_calc"))
        .def("compute_all", &ParallelBICalculator::compute_all,
            py::arg("graph"),
            py::arg("quotas"));
}