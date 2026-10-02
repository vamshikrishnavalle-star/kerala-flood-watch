# Stage 2 Model Selection Protocol

Date: 2026-10-03
Status: Locked Prior to Stage 2 Evaluation

## Selection Rules
1. **Optimization Metric**: Highest Out-of-Fold (OOF) PR-AUC inside the 2000–2018 training data.
2. **Tie-Breaker**: In the event of a tie (delta OOF PR-AUC < 0.005), the simpler model with lower false-alarm overhead wins.
3. **Partitioning**: Expanding-window `TimeSeriesSplit(n_splits=5)` strictly inside 2000–2018. The 2019–2024 test data is never used during selection.
4. **Architectural Guardrails**:
   - Range-clipping on linear models to eliminate negative dry-soil extrapolation artifacts.
   - Monotonicity checks across rainfall and soil features.
