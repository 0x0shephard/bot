**H100 GPU Index Pricing Methodology Report**
**Abbreviated Version**

October 2025

---

## Executive Summary

The market for high-performance AI compute has reached a pivotal stage of maturation. Once a niche resource accessible only to large technology firms and research institutions, GPU-accelerated compute is now a fundamental utility powering global economic activity. However, the market remains opaque, characterized by fragmented providers, inconsistent pricing structures, and a lack of standardized, trusted benchmarks. This environment creates significant friction for buyers, sellers, and investors, hindering efficient capital allocation and risk management.

This document establishes a comprehensive, rigorous, and reproducible methodology for creating a standardized benchmark for H100 GPU compute. The primary output is the H100 Compute Index Price, a single, volume-weighted, and performance-normalized value representing the fair market price of one hour of H100-equivalent GPU compute. Our analysis synthesizes data from a curated set of qualified cloud providers, including both global hyperscalers and specialized operators.

Drawing from established methodologies in commodity markets such as Nymex and ICE for crude oil, natural gas, and electricity futures, our approach prioritizes transparency, procedural rigor, and statistical validity. We explicitly address the market's defining characteristic: the substantial delta between public list prices and privately negotiated enterprise contracts. Our ongoing market research and intelligence gathering activities continuously refine estimates of hyperscaler discount structures. Discount rates are derived from analysis of actual market transactions, enterprise contract terms, and proprietary procurement intelligence.

The methodology employs a two-tiered weighting model that reflects the structural composition of the H100 market. Hyperscalers command the majority of total market weight, reflecting their dominant infrastructure position and revenue concentration. The remaining weight is allocated to specialized and regional providers, weighted proportionally by their estimated H100-specific revenue.

The resulting H100 Compute Index Price provides the foundational infrastructure necessary for the development of sophisticated financial instruments including spot exchanges, forward contracts, and futures markets. By establishing a transparent and reliable price benchmark, we aim to reduce information asymmetry, improve capital efficiency, and provide the essential tools for operators to finance capacity expansion and for consumers to hedge against price volatility.

---

## Scope and Objectives

### Scope

The scope of this methodology is precisely defined to ensure focus, analytical integrity, and benchmark reliability:

● **Asset Class:** Exclusively GPU-based cloud compute capacity. Does not consider CPUs, TPUs, or other AI accelerators at this stage.

● **Hardware Specification:** Confined to the NVIDIA H100 Tensor Core GPU and its major commercial variants. The H100 was selected due to its market ubiquity and role as the predominant workhorse for large-scale AI model development and deployment.

● **Service Type:** Covers Infrastructure-as-a-Service (IaaS) offerings where customers rent raw GPU compute hours. Explicitly excludes Platform-as-a-Service (PaaS) or Software-as-a-Service (SaaS) offerings that bundle proprietary software or managed services.

● **Provider Universe:** Encompasses a curated list of qualified cloud providers offering public access to H100 GPU infrastructure, including global hyperscalers and specialized operators.

● **Geographic Scope:** Data collection encompasses providers operating globally. All pricing data is normalized to United States Dollars (USD) for direct comparability. Regional cost variations are captured implicitly through provider pricing.

● **Time Unit:** The fundamental unit of measure is the price per GPU-hour, denominated in USD ($/GPU-Hour).

### Primary Objectives

● **To Establish a Definitive Price Index:** Calculate and publish a single, reliable, and representative index price for one hour of H100-equivalent compute that accurately reflects real-world market dynamics.

● **To Ensure Reproducibility and Transparency:** Document a complete, step-by-step procedure that can be independently replicated by third parties for verification and auditability.

● **To Standardize Performance Measurement:** Create and apply a quantitative framework for normalizing the performance of different H100 hardware variants against a common baseline, ensuring true apples-to-apples price comparisons.

● **To Support Financial Product Development:** Produce a benchmark of sufficient integrity to serve as the underlying reference for financial instruments, including spot exchanges, forwards, and futures contracts.

● **To Improve Market Efficiency:** Reduce information asymmetry between buyers and sellers by providing a trusted, data-driven benchmark grounded in actual transaction economics.

---

## Methodology Overview

### Provider Classification and Categorization

All qualified providers are classified into two categories:

**Hyperscalers (HS):** Large-scale cloud service providers characterized by massive global data center infrastructure, multi-region availability, and dominant market share. These providers serve the largest enterprise customers and frontier model developers, operating pricing models that bifurcate heavily between public list prices and private enterprise contracts.

**Non-Hyperscalers (Non-HS):** Specialized and regional cloud compute providers not designated as Hyperscalers. This group includes specialized AI infrastructure providers, regional operators, and smaller cloud platforms.

**Rationale:** This separation addresses the profound structural differences between these groups. Hyperscalers command the vast majority of market revenue, serve the largest customers, and operate pricing models with significant gaps between public and negotiated rates. Treating them as a single group would obscure critical market dynamics and produce an unrepresentative index.

### Data Collection Framework

For each qualified provider, a standardized set of data points is collected:

**Company Financials:**
- Annual revenue estimates
- H100-specific revenue attribution where available
- For public companies: disclosed cloud revenue segments with GPU attribution models
- For private companies: cross-validated estimates from business intelligence platforms

**Infrastructure Scale:**
- Estimated H100 GPU count
- Used to validate revenue figures and understand market capacity

**Pricing Data:**
- Public on-demand hourly prices
- Hardware variant specifications
- Instance configurations
- Currency denomination

**Discounting Structure (Hyperscalers Only):**
- Provider-specific discount rates derived from market intelligence
- Volume share under discounted contracts versus public retail rates
- Continuously updated as additional market data becomes available

### Data Sources and Validation

Data is sourced from authoritative channels prioritized as follows:

1. **Official Financial Documents:** SEC filings, earnings transcripts, investor presentations, IPO prospectus documents
2. **Official Company Disclosures:** Pricing pages, press releases, official blogs, GPU availability announcements
3. **Business Intelligence Platforms:** Reputable third-party platforms for private company estimates
4. **Industry Research:** Specialized AI infrastructure research and market intelligence
5. **Automated Web Scraping:** Custom Python scrapers using BeautifulSoup4 library for static sites and API endpoint analysis for dynamic pricing

All data points are cross-referenced with multiple independent sources. Official company disclosures are prioritized over third-party estimates. Conservative estimation practices are employed when uncertainty exists. Data vetting includes terms of service review, authentication checks, and robots.txt analysis to ensure compliant data collection.

### Performance Normalization

H100 GPUs are offered in multiple hardware variants with different performance characteristics. To ensure accurate price comparison, all pricing is normalized to a common performance baseline:

**Baseline Model:** H100 SXM5 variant designated as the performance baseline

**Normalization Method:** Performance ratio calculated using weighted hardware specifications:
- FP16 and FP64 TFLOPS (strongest price correlation)
- CUDA Cores and Tensor Cores (general compute capability)
- VRAM capacity (critical for large model training)
- Memory Bandwidth (data throughput)
- L2 Cache (latency reduction)

**Application:** Variant prices divided by performance ratio to yield performance-equivalent baseline pricing

**Weights:** Derived from linear regression analysis of hardware-price correlations across NVIDIA GPU product lines

### Weighting Model

A two-tiered weighting model ensures the index accurately reflects market structure:

**Tier 1: Categorical Weighting**
- Hyperscalers: Assigned majority total weight reflecting dominant market position and revenue concentration
- Non-Hyperscalers: Assigned remaining weight for specialized/regional providers

**Tier 2: Revenue-Proportional Weighting**
- Within each category, providers are weighted proportionally by H100-specific revenue
- Ensures the index reflects economic gravity of each market participant
- Prevents distortion from providers with minimal market impact

**Rationale:** Revenue-based weighting reflects that providers with greater market presence have larger impact on true market pricing dynamics.

### Hyperscaler Discount Adjustment

The final price for hyperscalers is not the public list price, but a blended effective price reflecting the mix of retail and discounted enterprise sales:

**Blended Price Formula:**
```
Effective_Price = (Public_Price × (1 - Discount_Rate)) × Volume_Discounted_Pct
                + (Public_Price) × (1 - Volume_Discounted_Pct)
```

**Discount Rate Sources:**
- Publicly documented committed use discount (CUD) and reserved instance (RI) structures
- Enterprise contract intelligence and procurement term analysis
- Market research and industry surveys
- Provider financial disclosures and revenue per GPU metrics
- Cross-validation with market transaction data

**Volume Split:**
- Large majority of hyperscaler H100 volume transacted under discounted contracts
- Remaining volume at or near public on-demand rates

**Update Protocol:**
- Discount rates reviewed quarterly or upon detection of significant market changes
- Updates incorporate new enterprise contract data and market intelligence
- All changes documented with effective dates and rationale

### Index Calculation Process

**Step 1: Provider Vetting**
- Identify candidate providers from market research and industry databases
- Vet for confirmed H100 availability, public pricing access, and data collection compliance
- Categorize as Hyperscaler or Non-Hyperscaler

**Step 2: Data Collection**
- Deploy automated scrapers for pricing data extraction
- Manual extraction for revenue data, discount structures, and GPU counts
- All raw data logged with source, timestamp, and analyst attribution

**Step 3: Data Standardization**
- Convert all pricing to USD using real-time exchange rates
- Normalize variant pricing to performance-equivalent baseline
- Aggregate multiple prices per provider to single representative value

**Step 4: Weight Calculation**
- Calculate categorical weights (Hyperscaler/Non-Hyperscaler allocation)
- Calculate revenue-proportional weights within categories
- Apply discount adjustments to hyperscaler pricing

**Step 5: Weighted Summation**
- Multiply each provider's effective price by its weight
- Sum all weighted contributions to derive final index

**Step 6: Validation and Publication**
- Compare against historical values, median, and simple average
- Verify weight sums and calculation integrity
- Timestamp and publish to database and blockchain oracle
- Archive all calculation artifacts

### Contingency and Fallback Protocols

**Provider Data Unavailability:**

In the event that a provider's pricing data cannot be retrieved due to temporary website downtime, API failure, terms of service changes, or other technical issues, the methodology employs a systematic fallback protocol:

- Weight allocated to unavailable provider is not discarded
- Weight is proportionally redistributed across remaining providers in the same category
- Redistribution maintains category totals (Hyperscaler/Non-Hyperscaler proportions)
- Redistribution is proportional to existing relative weights within category
- Ensures continuity of index calculation without category-level bias
- Maintains internal consistency of weighting framework

**Anomaly Detection:**

- Calculated prices deviating significantly from historical values trigger automatic rejection
- System substitutes anomalous calculations with last validated price
- Secondary validation protocol confirms whether anomaly represents error or genuine market shift
- All substitutions logged with source attribution for audit trail

**Data Quality Safeguards:**

- Invalid or incomplete data excluded from calculation rather than propagated
- Statistical outlier detection using IQR methodology
- Hyperscaler prices protected from outlier filtering to avoid systematic bias
- All excluded providers logged for investigation and follow-up

**Multi-Tier Fallbacks:**

- Zero or invalid calculation results invoke historical price retrieval
- Hyperscaler pricing follows three-tier cascade: real-time scrape → curated public price → proprietary research estimate
- Currency conversion falls back to hardcoded rates if API unavailable
- All fallback activations logged with source attribution

**Infrastructure Resilience:**

- Individual scraper failures isolated from pipeline continuation
- Blockchain submission employs retry protocol with exponential backoff
- Post-submission verification against on-chain stored values
- Automated data artifact preservation with defined retention periods

### Quality Assurance and Control

**Automated Validation:**
- Range checks on all numeric data
- Format validation against defined schemas
- Timestamp consistency verification
- Duplicate detection and removal
- Weight sum verification

**Manual Review:**
- Dual analyst review of final dataset
- Outlier investigation and documentation
- Random sample verification of scraped data
- Independent calculation verification

**Reproducibility:**
- All scripts version-controlled and publicly documented
- Discount rates explicitly specified with effective dates
- Parameters versioned and archived for historical reproduction
- Dependencies pinned to specific versions
- Complete audit trail from raw data to final index

**Inter-Analyst Testing:**
- Ring test protocol for periodic validation
- Independent teams calculate index from frozen dataset
- Results must fall within defined tolerance band
- Deviations trigger full procedural audit

### Uncertainty and Limitations

**Sources of Uncertainty:**
- Private company revenue estimates carry higher uncertainty than audited public company reports
- H100-specific revenue attribution relies on estimation models for diversified providers
- Enterprise discount rates are robust estimates continuously refined with new market data
- Market volatility can rapidly change pricing dynamics

**Key Limitations:**
- Spot/interruptible instance pricing not fully incorporated
- Single global figure without geographic granularity
- Pure price metric excluding service quality factors (SLAs, support, network performance)
- Periodic calculation represents snapshot in time, not real-time
- Limited visibility into actual private transaction prices

**Risk Mitigation:**
- Cross-validation from multiple independent sources
- Conservative estimation practices
- Periodic re-validation as new data emerges
- Regular methodology review and calibration
- Transparent documentation of all assumptions

---

## Index Applications

The H100 Compute Index is designed to support multiple critical market functions:

**Financial Products:**
- Spot exchange pricing reference
- Forward contract pricing
- Futures market underlying benchmark
- Options pricing spot reference

**Procurement and Planning:**
- Vendor quote benchmarking
- Budget planning and forecasting
- Contract negotiation market context
- Build vs. buy financial analysis

**Market Analysis:**
- Price discovery and transparency
- Market trend monitoring
- Competitive positioning analysis
- Generation-over-generation pricing evolution

**Investment and Financing:**
- Infrastructure financing revenue projections
- GPU asset valuation
- Market sizing and analysis
- Investment due diligence

---

## Methodology Governance

**Version Control:**
- All methodology changes versioned and documented
- Effective dates clearly specified
- Rationale for changes provided
- Historical versions maintained for reproducibility

**Update Frequency:**
- Index calculated on regular schedule (currently twice daily)
- Methodology reviewed quarterly
- Discount parameters updated as market data becomes available
- Emergency updates for material market changes

**Transparency:**
- Complete calculation procedures publicly documented
- All data sources disclosed
- Assumptions clearly stated
- Historical parameters maintained for reproducibility
- Blockchain publication for immutable record

**Validation:**
- Inter-analyst reproducibility testing
- Independent verification protocols
- Acceptance criteria for calculation variance
- Full audit procedures for deviations

---

## Conclusion

This methodology establishes a rigorous, transparent, and reproducible framework for calculating a trusted benchmark price for H100 GPU compute. By addressing the fundamental market inefficiency of opaque pricing through systematic data collection, performance normalization, revenue-weighted aggregation, and discount-adjusted pricing models, the H100 Compute Index provides the essential infrastructure for market efficiency, risk management, and financial product development.

The methodology draws from proven commodity market practices while addressing the unique characteristics of the GPU compute market, including performance heterogeneity across hardware variants and the substantial gap between public list prices and negotiated enterprise rates. Through continuous refinement of discount parameters, expansion of the provider universe, and rigorous quality assurance protocols, the index will evolve to maintain accuracy and representativeness as the market matures.




