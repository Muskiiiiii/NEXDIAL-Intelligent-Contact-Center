# Statistical Predictive Pacing Engine — NEXDIAL

## 1. Why Statistical Pacing Over Machine Learning?

Many enterprise contact centers make the architectural mistake of embedding black-box Machine Learning (ML) models (e.g. neural networks or deep regressors) directly into the pacing loop.

In practice, this creates severe failure modes:
1. **Explainability Deficit:** When an ML model over-dials and abandons 20 borrowers simultaneously, regulators (such as the FCC or FTC) require an exact algorithmic justification that black-box weights cannot provide.
2. **Cold-Start Fragility:** ML models degrade wildly during the first 30 minutes of a shift or when list demographics shift.
3. **Inference Latency:** Running ML inference in the hot dialing path introduces unnecessary latency compared to closed-form statistical formulas.

NEXDIAL implements a **transparent, auditable statistical pacing engine** combining Bayesian smoothed answer rates with Erlang-inspired queue capacity models.

---

## 2. Mathematical Formulation

### A. Bayesian Smoothed Answer Rate ($\hat{p}$)
Raw historical answer rates fluctuate wildly on small sample sizes. We compute a smoothed answer rate using an empirical Bayesian prior:

$$\hat{p} = \frac{N_{\text{completed}} \cdot p_{\text{historical}} + W_{\text{prior}} \cdot p_{\text{prior}}}{N_{\text{completed}} + W_{\text{prior}}}$$

Where:
- $N_{\text{completed}}$ = Total finished calls in the observation window.
- $p_{\text{historical}}$ = Empirical answer rate ($N_{\text{answered}} / N_{\text{completed}}$).
- $W_{\text{prior}} = 10$ (Prior weighting factor).
- $p_{\text{prior}} = 0.40$ (Conservative contact baseline).
- Clamped: $\hat{p} \in [0.05, 0.95]$ to prevent division by zero.

---

### B. Expected Near-Term Agent Releases ($E_{\text{releases}}$)
For agents currently in active conversation (`CONNECTED`), the probability that they will wrap up during the upcoming call setup window ($T_{\text{setup}} \approx 10\text{s}$) is estimated as:

$$E_{\text{releases}} = N_{\text{connected}} \cdot \min\left(1.0, \frac{T_{\text{setup}}}{\max(10.0, \bar{T}_{\text{talk}})}\right)$$

Where $\bar{T}_{\text{talk}}$ is the exponential moving average of talk time.

---

### C. Ringing Call Discount & Net Agent Capacity
Calls currently ringing at carrier switches will yield answers upon pickup. We discount these anticipated answers:

$$A_{\text{ringing}} = N_{\text{ringing}} \cdot \hat{p}$$

The net agent headroom expected when newly launched calls connect is:

$$\text{Capacity}_{\text{net}} = \max\left(0, (N_{\text{available}} + E_{\text{releases}}) - A_{\text{ringing}}\right)$$

---

### D. Raw Dials & Risk Buffer
To produce $\text{Capacity}_{\text{net}}$ answers from calls with answer rate $\hat{p}$:

$$\text{Dials}_{\text{raw}} = \frac{\text{Capacity}_{\text{net}}}{\hat{p}}$$

Applying the operator-configured Risk Factor $R \in [0.0, 0.5]$ (default 15%):

$$\text{Dials}_{\text{buffered}} = \lfloor \text{Dials}_{\text{raw}} \cdot (1 - R) \rfloor$$

---

### E. Hard Multiplier Upper Bound
To prevent catastrophic overdialing during carrier handshake delays, an absolute multiplier cap is enforced:

$$\text{Dials}_{\text{requested}} = \min\left(\text{Dials}_{\text{buffered}}, \lfloor 2.5 \cdot N_{\text{available}} \rfloor, N_{\text{queued\_borrowers}}\right)$$

The resulting $\text{Dials}_{\text{requested}}$ is forwarded to the **Safety Controller** for independent verification.
