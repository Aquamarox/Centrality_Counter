#include "CombinationCalculator.h"

CombinationCalculator::CombinationCalculator(const int max_n) : max_n(max_n) {
    comb.assign(max_n + 1, std::vector<long long>(max_n + 1, 0));
    
    for (int n = 0; n <= max_n; ++n) {
        comb[n][0] = 1;
        comb[n][n] = 1;
        
        for (int k = 1; k < n; ++k) {
            comb[n][k] = comb[n-1][k-1] + comb[n-1][k];
        }
    }
}

long long CombinationCalculator::get(const int n, const int k) const {
    if (k < 0 || k > n || n > max_n) return 0;
    return comb[n][k];
}

long long CombinationCalculator::sum_up_to(const int n, const int m) const {
    long long result = 0;
    for (int k = 0; k <= m; ++k) {
        result += get(n, k);
    }
    return result;
}