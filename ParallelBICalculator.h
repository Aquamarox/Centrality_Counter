#ifndef PARALLEL_BI_CALCULATOR_H
#define PARALLEL_BI_CALCULATOR_H

#include "CombinationCalculator.h"
#include <vector>

class ParallelBICalculator {
private:
    int k;
    int num_threads;
    const CombinationCalculator& comb_calc;

public:
    ParallelBICalculator(int k, int num_threads, const CombinationCalculator& calc);

    // смотри реализацию!
    std::vector<long long> compute_all(const std::vector<std::vector<double>>& graph,
                                      const std::vector<double>& quotas) const;
};

#endif