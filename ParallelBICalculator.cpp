#include <chrono>
#include <algorithm>
#include <functional>
#include "ParallelBICalculator.h"
#include "BIVertexCalculator.h"

#ifdef _OPENMP
#endif

using namespace std;
using namespace chrono;

ParallelBICalculator::ParallelBICalculator(const int k, const int num_threads,
                                         const CombinationCalculator& calc)
    : k(k), num_threads(num_threads), comb_calc(calc) {}




vector<long long> ParallelBICalculator::compute_all(
    const vector<vector<double>>& graph,
    const vector<double>& quotas) const {

    const int n = static_cast<int>(graph.size());
    vector<long long> results(n, 0);
    vector<vector<double>> all_sorted_weights(n);


    //запись весов в большой массив [][] + убывающая сортировка
#pragma omp parallel for num_threads(num_threads)
    for (int i = 0; i < n; ++i) {
        vector<double> weights;
        for (int j = 0; j < n; ++j) {
            if (j != i && graph[j][i] > 0) {
                weights.push_back(graph[j][i]);
            }
        }
        sort(weights.begin(), weights.end(), greater<double>());
        all_sorted_weights[i] = weights;
    }

    //непосредственно вычисление индексов для каждой вершины
#pragma omp parallel for num_threads(num_threads) schedule(dynamic, 5)
    for (int i = 0; i < n; ++i) {
        BIVertexCalculator calculator(k, comb_calc);
        results[i] = calculator.compute_for_vertex(all_sorted_weights[i], quotas[i]);
    }

    return results;
}