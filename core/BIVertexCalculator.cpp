#include "BIVertexCalculator.h"
#include <algorithm>
#include <cmath>

bool MemoState::operator==(const MemoState &other) const {
    return idx == other.idx &&
           size == other.size &&
           remaining == other.remaining &&
           sum_int == other.sum_int;
}

size_t MemoStateHash::operator()(const MemoState &s) const {
    const size_t h1 = std::hash<int>()(s.idx);
    const size_t h2 = std::hash<int>()(s.size);
    const size_t h3 = std::hash<int>()(s.remaining);
    const size_t h4 = std::hash<long long>()(s.sum_int);
    return ((h1 ^ (h2 << 1)) >> 1) ^ (h3 << 1) ^ h4;
}

BIVertexCalculator::BIVertexCalculator(int k, const CombinationCalculator &calc)
    : k(k), comb_calc(calc) {
}

long long BIVertexCalculator::sum_to_int(const double sum) {
    return static_cast<long long>(std::round(sum * 100.0));
}

long long BIVertexCalculator::dfs(const std::vector<double> &weights, const double quota, const int idx,
                                  const double current_sum, const int size,
                                  const std::vector<double> &prefix_sums,
                                  std::unordered_map<MemoState, long long, MemoStateHash> &memo) const {
    const int remaining = static_cast<int>(weights.size()) - idx;

    if (current_sum >= quota - 1e-9) {
        const int max_add = std::min(k - size, remaining);
        return comb_calc.sum_up_to(remaining, max_add);
    }

    if (idx == static_cast<int>(weights.size()) || remaining == 0 || size == k) {
        return 0;
    }

    const MemoState state{idx, size, remaining, sum_to_int(current_sum)};
    const auto it = memo.find(state);
    if (it != memo.end()) {
        return it->second;
    }

    const double best_possible = current_sum +
                           prefix_sums[idx + std::min(k - size, remaining)] -
                           prefix_sums[idx];
    if (best_possible < quota - 1e-9) {
        memo[state] = 0;
        return 0;
    }

    if (current_sum + weights.back() >= quota - 1e-9) {
        const int max_add = std::min(k - size, remaining);
        const long long result = comb_calc.sum_up_to(remaining, max_add) - 1;
        memo[state] = result;
        return result;
    }

    const long long take = dfs(weights, quota, idx + 1,
                               current_sum + weights[idx], size + 1,
                               prefix_sums, memo);

    const long long skip = dfs(weights, quota, idx + 1,
                               current_sum, size,
                               prefix_sums, memo);

    const long long result = take + skip;
    memo[state] = result;
    return result;
}

long long BIVertexCalculator::compute_for_vertex(const std::vector<double> &incoming_weights,
                                                 const double quota) const {
    if (incoming_weights.empty()) {
        return 0;
    }

    if (quota == 0) {
        const int m = static_cast<int>(incoming_weights.size());
        return comb_calc.sum_up_to(m, std::min(k, m)) - 1;
    }

    std::vector<double> weights = incoming_weights;
    std::sort(weights.begin(), weights.end(), std::greater<double>());
    const int m = static_cast<int>(weights.size());

    std::vector<double> prefix_sums(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        prefix_sums[i + 1] = prefix_sums[i] + weights[i];
    }

    std::unordered_map<MemoState, long long, MemoStateHash> memo;
    return dfs(weights, quota, 0, 0.0, 0, prefix_sums, memo);
}
