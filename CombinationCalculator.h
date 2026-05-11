#ifndef COMBINATION_CALCULATOR_H
#define COMBINATION_CALCULATOR_H

#include <vector>

//работа с перестановками C(n,m)
class CombinationCalculator {
private:
    std::vector<std::vector<long long>> comb;
    int max_n;
    
public:
    explicit CombinationCalculator(int max_n);
    long long get(int n, int k) const;

    //возвращает сумму C(n,0) + C(n,1) + ... + C(n,m)
    long long sum_up_to(int n, int m) const;
};

#endif