#ifndef BI_VERTEX_CALCULATOR_H
#define BI_VERTEX_CALCULATOR_H

#include "CombinationCalculator.h"
#include <vector>
#include <unordered_map>

// Структура для запоминания траекторий
struct MemoState {
    int idx;            // Текущее ребро
    int size;           // Кол-во взятых ребер взяли
    int remaining;      // Кол-во оставшихся ребер
    long long sum_int;  // Сумма взятых ребер

    // Операция сравнения
    bool operator==(const MemoState& other) const;
};

struct MemoStateHash {
    size_t operator()(const MemoState& s) const;
};

// Расчет индекса для одной вершины
class BIVertexCalculator {
private:

    // Главный метод - поиск всех подходящих групп
    long long dfs(const std::vector<double>& weights,
                  double quota,
                  int idx,
                  double current_sum, int size,
                  const std::vector<double>& prefix_sums,
                  std::unordered_map<MemoState, long long, MemoStateHash>& memo) const;


    int k;                                  // Максимальная мощность подмножеств
    const CombinationCalculator& comb_calc; // Таблица сочетаний

    //округляем сумму до ключа, чтоб более точно точно  искать по ключу значения
    static long long sum_to_int(double sum);


public:
    // Конструктор класса
    BIVertexCalculator(int k, const CombinationCalculator& calc);

    //public-часть главного метода
    long long compute_for_vertex(const std::vector<double>& incoming_weights,
                                double quota) const;
};

#endif