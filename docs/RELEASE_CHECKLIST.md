# Release Readiness Checklists

Pre-launch verification for commercial projects. Keep in each project's `/docs` folder.

---

## PyLearn Release Checklist

**Status:** Released (v1.0.0, Feb 2026)

### IP & Licensing
- [x] Copyright notice added to all files
- [x] Trademark search completed ("PyLearn")
- [x] License selected (recommend: MIT or Apache 2.0)
- [x] CONTRIBUTING.md created for open-source flow
- [x] Dependencies audited for license compatibility

### Documentation
- [x] README complete with examples
- [x] API documentation generated
- [x] Installation guide written
- [x] Getting started guide written
- [x] Architecture docs for contributors

### Code Quality
- [x] Test coverage >80%
- [x] All tests passing
- [x] Linting passes (pylint/flake8)
- [x] Type checking passes (mypy)
- [x] No security issues (bandit scan)

### Performance & Stability
- [x] Performance baseline established
- [x] Memory usage profiled
- [x] Edge cases tested
- [x] Error handling comprehensive
- [x] Logging appropriate for production

### Launch Prep
- [x] PyPI account setup
- [x] Package naming finalized
- [x] GitHub repo created (if going open source)
- [x] Release notes drafted
- [x] Landing page/demo ready
- [x] Marketing plan linked: See `go-to-market-plan.md`

---

## F1 Prediction Model Release Checklist

**Status:** In Progress (Q2 2026 target - Freemium SaaS)

### IP & Licensing
- [ ] Data source licensing verified (F1 official data requirements)
- [ ] Cannot use "Formula 1" trademark - name finalized
- [ ] Cannot use F1 logos - branding approved
- [ ] Analysis/commentary protection verified (fair use)
- [ ] Terms of service drafted

### Documentation
- [ ] Model explanation docs written
- [ ] API documentation complete
- [ ] User guide for predictions
- [ ] Methodology/limitations disclosed
- [ ] FAQ addressing F1-specific concerns

### Code Quality
- [ ] Backtest validation complete
- [ ] All edge cases handled
- [ ] Test coverage >75%
- [ ] Ablation studies documented
- [ ] No hardcoded credentials/secrets

### Performance & Stability
- [ ] Prediction accuracy baseline set
- [ ] Model robustness tested (race conditions, edge seasons)
- [ ] API response time <500ms
- [ ] Database query optimization verified
- [ ] Failover/redundancy plan documented

### Freemium Business Setup
- [ ] Pricing tiers defined
- [ ] Free tier vs paid tier split decided
- [ ] User authentication system ready
- [ ] Payment processing selected (Stripe/etc)
- [ ] Subscription management drafted

### Launch Prep
- [ ] Domain registered
- [ ] Landing page designed
- [ ] Demo predictions ready
- [ ] Beta testing group identified
- [ ] Marketing plan linked: See `go-to-market-plan.md`

---

## Balance of Power Release Checklist

**Status:** In Progress (Q3 2026 target - Data Platform)

### IP & Licensing
- [ ] Data sources catalogued and licensed
- [ ] Historical data sourcing verified (Cold War era)
- [ ] "Balance of Power" trademark checked (common IR term)
- [ ] Data licensing agreements reviewed
- [ ] Trademark registration plan (if needed)

### Documentation
- [ ] Data schema documented
- [ ] Database design documented
- [ ] API documentation complete (if exposing)
- [ ] Contributing guidelines for data submissions
- [ ] Historical accuracy review process documented

### Data Quality
- [ ] Data validation scripts written
- [ ] Missing data documented
- [ ] Source attribution complete
- [ ] Accuracy verified (expert review?)
- [ ] Data versioning system implemented

### Platform Stability
- [ ] Database performance tested
- [ ] Query optimization complete
- [ ] Backup/disaster recovery plan
- [ ] Data integrity checks automated
- [ ] Scale testing (if applicable)

### Multi-App Strategy
- [ ] Primary app target selected (wargame? educational? intel sim?)
- [ ] Data API design finalized
- [ ] App architecture documented
- [ ] Team/governance model for data platform

### Launch Prep
- [ ] Domain/brand finalized
- [ ] First application design started
- [ ] Landing page drafted
- [ ] Potential partnerships identified
- [ ] Marketing plan linked: See `go-to-market-plan.md`

---

## How to Use

1. **Copy to your project:**
   ```powershell
   Copy-Item "~/.claude/RELEASE_READINESS_CHECKLIST.md" `
       "C:\Users\tritl\OneDrive\Nate\PyLearn\docs\RELEASE_CHECKLIST.md"
   ```

2. **Check off items as completed**

3. **Update monthly** — Keep this visible, update every sprint

4. **Track blocker** — If an item is red/blocked, note it in CLAUDE.md

5. **Before launch** — All items must be checked ✅

---

## Quick Status

| Project | Readiness | Top Blocker | Target |
|---------|-----------|-------------|--------|
| PyLearn | 100% | — | Released |
| F1 | 60% | Freemium setup | Q2 2026 |
| BoP | 50% | App strategy | Q3 2026 |

