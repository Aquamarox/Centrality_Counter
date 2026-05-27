#ifndef PARALLEL_BI_CALCULATOR_H
#define PARALLEL_BI_CALCULATOR_H

#include "CombinationCalculator.h"
#include <vector>

// Производит параллельный рассчет индексов для всего графа
class ParallelBICalculator {
private:
    int k;                                  // Максимальная мощность подмножеств
    int num_threads;                        // Кол-во потоков
    const CombinationCalculator& comb_calc; // Таблица сочетаний

public:

    // Параллельный рассчет индексов для всего графа
    std::vector<long long> compute_all(const std::vector<std::vector<double>>& graph,
                                      const std::vector<double>& quotas) const;
    // Конструктор класса
    ParallelBICalculator(int k, int num_threads, const CombinationCalculator& calc);


};

#endif