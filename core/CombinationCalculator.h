#ifndef COMBINATION_CALCULATOR_H
#define COMBINATION_CALCULATOR_H

#include <vector>

// Работа с перестановками C(n,m)
class CombinationCalculator {
private:
    std::vector<std::vector<long long>> comb;  // Таблица сочетаний
    int max_n;                                 // Границы таблицы
    
public:
    // Получить С(n, k)
    long long get(int n, int k) const;

    // Возвращает сумму C(n,0) + C(n,1) + ... + C(n,m)
    long long sum_up_to(int n, int m) const;

    // Конструктор класса
    explicit CombinationCalculator(int max_n);
};

#endif