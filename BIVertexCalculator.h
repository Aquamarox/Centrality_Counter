#ifndef BI_VERTEX_CALCULATOR_H
#define BI_VERTEX_CALCULATOR_H

#include "CombinationCalculator.h"
#include <vector>
#include <unordered_map>

struct MemoState {
    int idx;            // текущее ребро
    int size;           // сколько ребер взяли
    int remaining;      // сколько ребер осталось рассмотреть
    long long sum_int;  // сумма взятых ребер

    //для сравнения хэшей
    bool operator==(const MemoState& other) const;
};

struct MemoStateHash {
    size_t operator()(const MemoState& s) const;
};

class BIVertexCalculator {
private:
    int k;
    const CombinationCalculator& comb_calc;

    //округляем сумму до ключа, чтоб более точно точно  искать по ключу значения
    static long long sum_to_int(double sum);

    //главный метод - поиск всех подходящих групп
    long long dfs(const std::vector<double>& weights, double quota, int idx,
                  double current_sum, int size,
                  const std::vector<double>& prefix_sums,
                  std::unordered_map<MemoState, long long, MemoStateHash>& memo) const;
    
public:
    BIVertexCalculator(int k, const CombinationCalculator& calc);

    //public-часть главного метода
    long long compute_for_vertex(const std::vector<double>& incoming_weights,
                                double quota) const;
};

#endif