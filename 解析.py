from scipy.stats import ttest_rel

web_scores = [6.6, 7.5, 5.9, 7.5, 8.4, 8.5]
llm_scores = [7.8, 7.5, 6.6, 7.3, 8, 7.8]

t_stat, p_value = ttest_rel(llm_scores, web_scores)

print(f"t値 = {t_stat:.3f}, p値 = {p_value:.4f}")