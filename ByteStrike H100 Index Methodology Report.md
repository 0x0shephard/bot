**ByteStrike H100 Index Pricing Methodology Report**

October 2025 

**Table of Contents** 

§1. Executive Summary 

§2. Scope and Objectives 

§3. Definitions and Abbreviations 

§4. Test Design and Rationale 

§5. Instruments, calibration, and Chain of Custody 

§6. Test Procedures and Protocols 

§7. Data Processing and Statistical Methods 

§8. Uncertainty, QA/QC, and Reproducibility 

§9. Results Synthesis and Benchmark Construction 

§10. Limitations, Assumptions, and Risk Assessment 

§11. Appendix A: Master Data Set 

§12. Appendix B: Worked Calculation Examples 

§**1\. Executive Summary** 

The market for high-performance Artificial Intelligence (AI) compute has reached a pivotal stage of maturation. Once a niche resource accessible only to large technology firms and research institutions, GPU-accelerated compute is now a fundamental utility powering global economic activity. However, the market remains opaque, characterized by fragmented providers, inconsistent pricing structures, and a lack of standardized, trusted benchmarks. This environment creates significant friction for buyers, sellers, and investors, hindering efficient capital allocation and risk management. 

This document establishes a comprehensive, rigorous, and reproducible methodology for creating a standardized benchmark for AI compute, specifically focusing on the NVIDIA H100 Tensor Core GPU, the current de facto standard for large-scale AI workloads. The primary output of this methodology is the H100 Compute Index Price, a single, volume-weighted, and performance-normalized value representing the fair market price of one hour of H100-equivalent GPU compute. Our analysis synthesizes data from 47 distinct cloud providers, a cohort that includes industry leaders such as Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP), as well as a broad spectrum of specialized and regional operators. 

Modeled on the formal methodologies employed in mature commodity markets such as Nymex and ICE  for crude oil and electricity, our approach emphasizes transparency, procedural rigor, and statistical validity. We address the market's key complexities, including the significant delta between public list prices and the privately negotiated enterprise discounts offered by hyperscalers, which our research indicates can range from 30% to over 60%. We also standardize for performance variations among different H100 hardware variants (e.g., SXM5, PCIe) using a regression-derived weighting model.

The methodology is designed to support the development of sophisticated financial instruments forwards and futures contracts, thereby enabling compute to be managed as a tradable commodity. By creating a transparent and reliable price benchmark, we aim to reduce information asymmetry, improve price discovery, and provide the foundational tools necessary for operators to finance capacity expansion and for consumers to hedge against price volatility. The ultimate vision is to professionalize, standardize, and financialize the AI compute market, creating an ecosystem where compute capacity is as liquid as any other global commodity. This report details every step of that process, from raw data collection to the final index calculation, providing a complete blueprint for establishing a trusted benchmark in this critical new asset class. 

§**2\. Scope and Objectives** 

§**2.1 Scope** 

The scope of this methodology is strictly defined to ensure focus, precision, and the integrity of the final benchmark. The boundaries of the analysis are as follows: 

● **Asset Class:** The methodology is confined exclusively to GPU-based cloud compute capacity. It does not consider Central Processing Units (CPUs), Google's Tensor Processing Units (TPUs), or other emerging types of AI accelerators at this stage. This focus is intended to create a pure-play benchmark for the dominant technology in the AI training and inference market. 

● **Hardware Specification:** The initial benchmark is exclusively focused on the NVIDIA H100 Tensor Core GPU, including all its major commercial variants (e.g., H100 SXM5, H100 PCIe, H100 NVL). The H100 was selected due to its market ubiquity and its role as the predominant workhorse for the development and deployment of large-scale AI models. Future iterations of this methodology may incorporate subsequent hardware generations, such as the Blackwell platform, as they achieve significant market penetration. 

● **Service Type:** The methodology covers Infrastructure-as-a-Service (IaaS) offerings where customers rent raw GPU compute hours. It explicitly excludes 

Platform-as-a-Service (PaaS) or Software-as-a-Service (SaaS) offerings that bundle proprietary software, managed services, or machine learning frameworks with the underlying compute. This distinction is critical for isolating the cost of the raw commodity. 

● **Provider Universe:** The analysis encompasses a curated list of 47 cloud providers. This list was distilled from an initial survey of over 300 potential entities and includes a representative mix of global hyperscalers and smaller, specialized firms to ensure the benchmark reflects the full breadth of the competitive landscape. 

● **Geographic Scope:** The data collection encompasses providers operating globally. All pricing data, regardless of its original currency (e.g., EUR for providers like Scaleway, INR for providers like JarvisLabs), is normalized to a single standard currency, the United States Dollar (USD), to ensure direct comparability. Regional cost variations are captured implicitly through provider pricing but are not isolated as a separate factor in the current version of the index. 

● **Time Unit:** The fundamental unit of measure for the index is the price per GPU-hour, denominated in USD ($/GPU-Hour). This unit was chosen for its granularity and its common usage in on-demand cloud pricing models.

§**2.2 Primary Objectives** 

The development of this methodology is guided by a set of clear and measurable primary objectives: 

● **To Establish a Definitive Price Index:** To calculate and publish a single, reliable, and representative index price for one hour of H100-equivalent compute. This index must accurately reflect real-world market dynamics by accounting for provider scale, hardware variance, and the prevalent discounting practices that define the true cost of compute for large consumers. 

● **To Ensure Reproducibility and Transparency:** To document a complete, step-by-step procedure that can be independently replicated by a third party to verify the index price. All data sources, transformations, and statistical methods shall be clearly defined to allow for full auditability. 

● **To Standardize Performance Measurement:** To create and apply a quantitative framework for normalizing the performance of different H100 hardware variants against a common baseline (the H100 SXM5). This ensures a true "apples-to-apples" price comparison based on delivered computational value rather than nominal hardware labels. 

● **To Create a Foundational Benchmark for Financial Products:** To produce a benchmark of sufficient integrity and reliability to serve as the underlying reference for financial instruments, including spot exchanges, forwards, and futures contracts. This objective is central to enabling effective risk management for both producers and consumers of compute capacity. 

● **To Improve Market Efficiency:** To reduce the significant information asymmetry that currently exists between buyers and sellers of compute. By providing a trusted, data-driven benchmark, we aim to improve price discovery and foster a more liquid, competitive, and efficient marketplace for this essential resource. 

§**3\. Definitions and Abbreviations** 

● **AI:** Artificial Intelligence. 

● **API:** Application Programming Interface. A method for computer systems to communicate. 

● **Compute Index Price:** The final, singular price point produced by this methodology, representing the market value of one GPU-hour. 

● **CUD:** Committed Use Discount. A discount offered by providers like Google Cloud in

   exchange for a commitment to use a minimum level of resources for a specified term.   

● **GPU:** Graphics Processing Unit. A specialized electronic circuit designed for parallel computation.     

  ● **GPU-Hour:** The fundamental unit of compute being priced. It represents the exclusive use of one physical H100 GPU (or its normalized equivalent) for a continuous period of one hour. 

  ● **H100:** The NVIDIA H100 Tensor Core GPU, based on the Hopper architecture.  
● **Hyperscaler (HS):** A large-scale cloud service provider characterized by massive global data center infrastructure and a dominant share of the cloud computing market. For the purpose of this report, the five designated hyperscalers are Amazon Web Services (AWS), Microsoft Azure, Google Cloud Platform (GCP), Oracle Cloud Infrastructure (OCI), and CoreWeave. 

● **IaaS:** Infrastructure-as-a-Service. A cloud computing model where providers host infrastructure components on behalf of users. 

● **Non-Hyperscaler (Non-HS):** Any cloud compute provider not designated as a Hyperscaler. This group includes the other 42 providers analyzed, such as Lambda Labs, Voltage Park, and Hyperstack. 

● **NVL:** A specific hardware configuration of the H100 GPU featuring NVLink interconnects, often in multi-GPU servers. 

● **PCIe:** Peripheral Component Interconnect Express. A standard interface for connecting high-speed components. The H100 PCIe is a variant designed for this interface, differing in performance characteristics from the SXM variant. 

● **RI:** Reserved Instance. A discount offering similar to a CUDA, commonly used by AWS. 

● **SXM:** A high-density server socket design used for high-performance H100 variants, offering superior interconnect and power delivery compared to PCIe. The H100 SXM5 is designated as the baseline model for performance normalization in this report. 

● **TFLOPS:** Tera Floating-point Operations Per Second. A measure of a processor's performance. 

§**4\. Test Design and Rationale** 

The integrity of the Compute Index Price is fundamentally dependent on the quality and breadth of the input data. The data collection process is designed to be systematic, comprehensive, and auditable, mirroring the rigor of data gathering in established commodity markets. This section outlines the design of our data collection "test" and the rationale behind its structure. 

§**4.1 Provider Universe and Categorization** 

The process begins by identifying a broad universe of potential providers offering public cloud access to NVIDIA H100 GPUs. This universe initially included over 300 entities identified through market scans, industry reports, and partner lists. A rigorous vetting process is then applied to distill this list into a set of 47 qualified data sources. The vetting criteria include public availability of pricing, evidence of operational H100 infrastructure, and compliance with our data collection terms (i.e., not explicitly prohibiting scraping). 

● **Provider Categorization:** A critical step in the design is the binary classification of all 47 providers into two categories: Hyperscalers (HS) and Non-Hyperscalers (Non-HS). 

○ **Rationale:** This separation is necessary due to the profound structural differences between these two groups. Hyperscalers command the vast majority of market  
revenue, serve the largest customers, and operate pricing models that bifurcate heavily between public list prices and private enterprise contracts. Treating them as a single monolithic group would obscure these critical market dynamics and produce a skewed, unrepresentative index. 

○ **Designated Hyperscalers:** The five designated hyperscalers are AWS, Azure, GCP, OCI, and CoreWeave. They were selected based on their market share, reported infrastructure scale, and public financial reporting. 

§**4.2 Data Point Specification** 

For each qualified provider, a specific set of data points is collected. This standardized data schema ensures consistency across the entire dataset. 

● **Company Financials:** 

○ Total Annual Revenue (USD): The most recently reported or reliably estimated total annual revenue for the provider. This is a primary input for the weighting model. For public

Companies, we use the reported fiscal year revenue for the cloud division of the business. For private companies we rely on cross-validated estimates from business intelligence platforms. 

○ H100-Specific Revenue (USD): Where available, the estimated annual revenue derived specifically from H100 GPU services. This is a more precise input for weighting.

● **Infrastructure Scale:** 

○ Total H100 GPU Count: The estimated number of H100 GPUs operated by the provider. This is used to validate revenue figures and understand market scale. 

● **Pricing Data:** 

○ **Public On-Demand Price ($/Hour):** The publicly listed, pay-as-you-go hourly price for each H100 variant offered. 

○ **Hardware Variant:** The specific model of the H100 GPU associated with the price (e.g., SXM5, PCIe 80GB). 

○ **Instance Configuration:** The number of GPUs included in the priced instance (e.g., 8x H100). 

○ **Currency:** The currency in which the price is listed. 

● **Discounting Structure (Hyperscalers Only):** 

○ **Realized Enterprise Discount (%):** The estimated typical discount percentage achieved by large enterprise customers on H100 compute relative to the public  
on-demand price.

○ **Volume Share Under Discount (%):** The estimated percentage of a hyperscaler's total H100 compute volume that is sold under discounted contracts versus at public retail rates.

§**4.3 Rationale for Data Selection** 

Each data point is chosen for a specific purpose in the index calculation: 

● Revenue and GPU Counts are essential for establishing the market weight of each provider. The principle is that providers with greater revenue and infrastructure have a larger impact on the true market price. 

● Public Pricing Data serves as the raw, unadjusted input for the price calculation. Collecting prices for all variants is necessary for the subsequent performance normalization step. 

● Discounting Data is arguably the most critical element for market accuracy. The public list prices of hyperscalers are often not representative of the actual prices paid by the largest consumers of compute. Ignoring these deep, high-volume discounts would result in a significantly inflated and misleading index. This data allows the model to correct for that skew. 

§**5\. Instruments, Calibration, and Chain of Custody** 

The credibility of the benchmark rests upon a meticulous and transparent approach to data sourcing and management, analogous to the instrumentation, calibration, and chain of custody protocols in physical sciences. A formal chain of custody is maintained to ensure that every data point in the final index calculation can be traced back to its origin and that all transformations are documented. 

§**5.1 Instrumentation: Primary Data Sources** 

In the context of this methodology, "instrumentation" refers not to physical sensors but to the authoritative sources from which data is derived. We prioritize sources in the following order of authority: 

1\. **Official Financial Documents:** SEC filings (10-K, 8-K, 10-Q reports) and IPO prospectus documents (S-1 filings). These are considered the most reliable sources for revenue data.

2\. **Official Company Disclosures:** Company websites (specifically pricing pages), press  
releases, and official blogs announcing GPU availability or pricing updates. These are the primary source for public pricing information and confirmed minimum GPU counts.

3\. **Business Intelligence Platforms:** Reputable third-party platforms such as ZoomInfo, Growjo, Crunchbase, and Sacra. These are used primarily for estimating revenue and scale for private companies where official documents are unavailable.

4\. **Specialized Industry Research:** Reports and analyses from industry-specific sources are used to cross-validate GPU counts and market trends. 

§**5.2 Calibration: Data Validation and Cross-Referencing** 

"Calibration" is the process of verifying the accuracy of the collected data. No single data point is accepted without validation. 

● **Cross-Referencing:** Every key data point (especially revenue and GPU counts for private companies) is cross-referenced with at least two independent sources. Discrepancies are flagged for reconciliation, as documented in Appendix C.

● **Prioritization:** Official company disclosures are always prioritized over third-party estimates. If a company's pricing page contradicts a price listed on a third-party aggregator, the official source is used. 

● **Conservative Estimation:** When data is presented as a range, a conservative estimate or the midpoint is chosen, and the choice is documented. For GPU counts, confirmed minimums from official announcements are used as the floor for estimates. 

● **Outlier Analysis:** Any data point that deviates significantly from industry benchmarks or peer providers is subject to additional scrutiny and requires further validation before being accepted into the Master Data Set. 

§**5.3 Chain of Custody: Data Logging and Integrity** 

A formal chain of custody ensures data integrity from collection to final analysis. 

● **Raw Data Log:** All raw data collected from primary sources is logged in an immutable format. This includes the data point itself, the source, the timestamp of collection, and the analyst responsible. 

● **Data Vetting and Scrapability Checks:** Before automated scraping, each provider's website undergoes a three-step check: 

1\. **Terms of Service Review:** A manual review to ensure data scraping is not explicitly prohibited. 

2\. **Authentication Check:** Verification that pricing is publicly accessible.  
3\. **Robots.txt Analysis:** Inspection of the /robots.txt file to ensure automated access to pricing endpoints is not disallowed.. 

● **Data Transformation Log:** Every transformation applied to the raw data is logged. This includes currency conversions (with the exchange rate and timestamp used), performance normalization calculations, and weighting applications. Each step is traceable. 

● **Data Signing and Verification:** The final, curated Master Data Set is digitally signed with a checksum (e.g., SHA-256). This allows for verification that the dataset used in the final index calculation has not been altered or corrupted. Time synchronization is used across all data collection systems to ensure consistent timestamps. 

§**6\. Test Procedures and Protocols** 

This section details the step-by-step operational procedure for constructing the H100 Compute Index Price, moving from raw data collection to a single, finalized value. This protocol is designed to be followed rigorously to ensure consistency and reproducibility. 

**Step 1: Provider Identification and Vetting** 

● A candidate list of over 300 global cloud providers is compiled from market research, industry publications, and public databases. 

● Each provider is vetted for confirmed public offerings of NVIDIA H100 GPU instances. 

● Each confirmed provider's website and terms of service are subjected to the three-step scrapability check (Terms of Service review, authentication check, robots.txt analysis) as detailed in §5.3. 

● The vetted list is reduced to the final cohort of 47 qualified providers. 

● Each of the 47 qualified providers is categorized as either a Hyperscaler or a Non-Hyperscaler. 

**Step 2: Automated and Manual Data Extraction** 

● A series of custom scrapers, written in Python using the BeautifulSoup4 library, are deployed to extract pricing data from the websites of the qualified providers. 

● Two primary scraping techniques are used, tailored to the structure of each target website: 

○ **Regex Parsing:** For static websites where pricing is presented in clean HTML tables, regular expressions are used to parse and extract H100 model names and corresponding prices. 

○ **API Calls:** For dynamic websites that load pricing data via JavaScript, network traffic is analyzed to identify and leverage underlying pricing API endpoints. The JSON responses from these endpoints are parsed to extract the required data. 

● For data not available via scraping (e.g., revenue for private companies, discount structures), manual extraction is performed from the authoritative sources defined in  
§5.1. This includes detailed analysis of SEC filings for public companies and cross-validation of estimates from business intelligence platforms for private entities.   
● All extracted raw data is stored in a structured JSON file, forming the initial raw data log. 

**Step 3: Data Cleaning and Standardization** 

● The raw JSON data is converted to a CSV format for processing and analysis. 

● A currency conversion protocol is executed: 

○ An API from a real-time foreign exchange rate service is queried to get the latest conversion rates. 

○ All prices not denominated in USD are converted to USD using the fetched rates. The conversion rate and timestamp are logged for auditability. 

● The dataset is reviewed for completeness and consistency. Any missing critical values are flagged for further investigation or imputation based on clearly defined rules. 

**Step 4: Performance Normalization** 

● The H100 SXM5 variant is established as the baseline model for performance. 

● For every price point associated with a non-SXM variant (e.g., PCIe, NVL), a normalization procedure is applied to adjust its price to a performance-equivalent SXM price. 

● The normalization is calculated as: Normalized Price \= PricePerGPU / PerformanceRatio. 

● The PerformanceRatio is a weighted sum of the variant's key hardware specifications relative to the SXM5 baseline. The calculation is detailed in §7.1. This step is crucial for ensuring all prices in the dataset represent the cost for a standardized unit of computational performance. 

**Step 5: Data Aggregation per Provider** 

● After normalization, each provider may still have multiple price points (e.g., for different instance sizes or from original SXM offerings). 

● To derive a single price value for each provider, the arithmetic mean of all its normalized prices is calculated. 

● For providers that only offer bundles (e.g., an 8x H100 server), the normalized bundle price is first divided by the number of GPUs in the bundle to get a per-GPU price before averaging. 

**Step 6: Weighting and Final Index Calculation** 

● The final, single price from each of the 47 providers is taken forward for the weighted summation. 

● Provider weights are calculated and applied according to the two-tiered, discount-adjusted model detailed in §7.2. 

● The final H100 Compute Index Price is calculated by taking the weighted sum of the single normalized price from all qualified providers. The formula is: Index Price \= Σ (Provider\_Price\_i \* Provider\_Weight\_i).

**Contingency Plan (Fallback Protocol):**

● In the event that a provider’s pricing data cannot be retrieved (e.g., due to temporary website downtime, API failure, or data access restrictions), the weight allocated to that provider is not discarded. Instead, it is proportionally redistributed across the remaining providers in the same category (Hyperscaler or Non-Hyperscaler).

● Redistribution is executed in proportion to the existing weights of the surviving providers within that category, thereby preserving the total category contribution (e.g., 60% for Hyperscalers, 40% for Non-Hyperscalers).

● This ensures continuity of the Index calculation, prevents category-level bias from missing data, and maintains internal consistency of the weighting framework.

§**7\. Data Processing and Statistical Methods** 

This section provides the specific formulae and quantitative methods used in the data processing pipeline. These methods are designed to transform raw, heterogeneous data into a standardized, comparable, and accurately weighted set of inputs for the final index calculation. 

§**7.1 Performance Normalization Model** 

The purpose of normalization is to make the prices of different H100 variants (PCIe, NVL) comparable to the baseline SXM5 model. This is achieved by adjusting their prices based on their relative performance.

● Performance Ratio Formula: 

PerformanceRatio \= Σ (Weight\_spec \* (Spec\_variant / Spec\_baseline)) 

Where: 

○ Spec\_variant is the hardware specification value for the variant being normalized (e.g., PCIe CUDA cores). 

○ Spec\_baseline is the corresponding value for the H100 SXM5. 

○ Weight\_spec is the predetermined weight for that hardware specification, derived from a linear regression analysis of the correlation between various hardware specifications and market pricing across the entire NVIDIA GPU lineup. 

● Specification Weights: 

The following hardware components and their corresponding weights are used in the calculation. These weights reflect the relative importance of each component in determining the overall performance and market price of an H100-class GPU. The analysis showed that FP16 and FP64 throughput were the most significant predictors of price. 

| Hardware Specification  | Assigned Weight  | Rationale |
| :---- | :---- | :---- |
| FP16 TFLOPS  | 0.155983  | Strongest correlation with general computational capability |
| FP64 TFLOPS  | 0.155958  | Strong correlation for HPC and scientific computing. |
| CUDA Cores  | 0.144435  | General-purpose compute capability. |

Tensor Cores 0.144435 Specialized for AI matrix operations.

| VRAM (GB)  | 0.140570  | Critical for large model  training; a major cost driver. |
| :---- | :---- | :---- |
| Memory Bandwidth (GB/s)  | 0.138890  | Essential for preventing data bottlenecks. |
| L2 Cache (MB)  | 0.119730  | Reduces latency and  improves sustained  performance. |

● Normalization Application: 

Normalized Price \= (Price\_USD / Num\_GPUs\_in\_Instance) / PerformanceRatio 

§**7.2 Provider Weighting Model** 

A two-tiered weighting model is used to ensure the index accurately reflects the structure of the compute market. 

● Tier 1: Categorical Weighting 

The entire market is divided into two segments with fixed total weights: ○ **Hyperscalers (HS):** Assigned a total weight of 60%. 

○ **Non-Hyperscalers (Non-HS):** Assigned a total weight of 40%. 

○ *Rationale:* This 60/40 split reflects the dominant market position and revenue concentration of the five designated hyperscalers, which together account for the majority of global cloud revenue. 

● **Tier 2: Revenue-Proportional Weighting within Categories** 

○ Non-Hyperscalers: The 40% total weight is distributed among the 42 Non-HS providers in direct proportion to their individual annual revenues. 

Weight\_Non-HS\_i \= 0.40 \* (Revenue\_i / Total\_Revenue\_All\_Non-HS) 

○ **Hyperscalers (Discount-Adjusted):** The 60% total weight is distributed among the five HS providers based on their revenue, but the price used for each provider is a blended price that accounts for enterprise discounts. 

● Hyperscaler Blended Price Formula: 

The final price used for a hyperscaler is not its public list price, but a blended price reflecting the mix of retail and discounted sales. 

Blended\_Price\_HS\_i \= (Price\_Scraped \* (1 \- Pct\_Discount)) \* Pct\_Volume\_Discounted \+ (Price\_Scraped) \* (1 \- Pct\_Volume\_Discounted) 

The final weight for the hyperscaler is then applied to this blended price. Weight\_HS\_i \= 0.60 \* (Revenue\_i / Total\_Revenue\_All\_HS) 

Index Contribution\_HS\_i \= Blended\_Price\_HS\_i \* Weight\_HS\_i 

● Final Index Price Formula: 

Index Price \= Σ (Index Contribution\_HS\_i) \+ Σ (Price\_Non-HS\_i \* Weight\_Non-HS\_i)  
§**8\. Uncertainty, QA/QC, and Reproducibility** 

§**8.1 Sources of Uncertainty** 

The primary sources of uncertainty in this methodology are inherent to the opacity of the private markets and are transparently acknowledged. 

● **Private Company Data:** Revenue and GPU fleet sizes for private companies are estimates derived from third-party platforms. While we cross-validate these figures, they carry a higher degree of uncertainty than the audited financial reports of public companies. The uncertainty is typically in the range of \+/- 20%.

● **H100 Revenue Attribution:** For diversified providers, the revenue specifically attributable to H100 services is an estimation based on compute's share of total cloud revenue and H100's share of the GPU fleet. 

● **Discounting Data:** The realized enterprise discounts and the volume share of compute sold under these discounts are not publicly disclosed by hyperscalers. The figures used are robust estimates based on extensive market research, but they remain an approximation and are the most sensitive inputs in the model. 

● **Market Volatility:** The GPU compute market is highly dynamic. Prices can change rapidly due to supply shifts, demand surges, or new hardware releases. The index represents a snapshot in time, and its currency diminishes over a quarterly cycle. 

§**8.2 Quality Assurance and Quality Control (QA/QC)** 

A series of QA/QC checks are embedded in the process to minimize errors. 

● **Automated Range Checks:** All collected numeric data is automatically checked against predefined valid ranges.

● **Timestamp Monotonicity Checks:** All data logs are checked to ensure timestamps are sequential and consistent. 

● **Duplicate Detection:** The dataset is programmatically de-duplicated at the provider and instance level. 

● **Manual Review:** The final Master Data Set undergoes a full manual review by at least two analysts prior to the final index calculation to catch any anomalies missed by automated checks. 

§**8.3 Inter-Analyst Reproducibility** 

The methodology is designed to be fully reproducible by an independent party. 

● **Ring Test Design:** A "ring test" protocol is established for periodic methodology validation. A frozen, raw dataset is provided to two independent teams of analysts. 

● **Procedure:** Both teams must follow the procedures detailed in this document to independently calculate a final index price.  
● **Statistical Analysis:** The results from both teams are compared. The variance between their final index values and intermediate calculations is analyzed. 

● **Acceptance Criteria:** The inter-analyst reproducibility is considered acceptable if the final index prices from both teams are within a 2% tolerance band. Deviations greater than this threshold trigger a full audit of the procedures.

§**8.4 Automated Resilience and Contingency Protocols**

The index calculation pipeline incorporates multiple layers of automated fault tolerance and contingency mechanisms to ensure continuous, reliable operation even in the presence of data anomalies, infrastructure failures, or market volatility. These protocols operate autonomously and are designed to preserve index integrity while maintaining uninterrupted service. This section details the comprehensive suite of safeguards embedded within the operational implementation.

§**8.4.1 Price Anomaly Detection and Rejection**

A critical safeguard against data corruption, market manipulation, and systemic errors is the automated detection and rejection of anomalous price movements.

● **Significant Change Detection Protocol:**

○ Any calculated index price that deviates by 50% or more from the most recently validated and stored price is automatically flagged as anomalous and rejected. This threshold was selected based on historical market analysis, which indicates that legitimate H100 price movements exceeding this magnitude are exceptionally rare and typically indicative of data collection errors rather than genuine market shifts.

○ Upon detection of such an anomaly, the system automatically substitutes the newly calculated price with the last validated price stored in the historical record. This carry-forward mechanism ensures index continuity and prevents the publication of potentially erroneous values.

○ The substitution event is logged with a specific source designation (carry\_forward\_prev) in the price history database, creating a complete audit trail of when and why automated interventions occurred.

● **Automated Revalidation Mechanism:**

○ When a significant price movement is detected during an automated calculation run (e.g., via scheduled cron job), the system initiates a secondary validation protocol. A marker file (.price\_change\_triggered) is created and committed to the version control repository, which triggers the pipeline orchestration system to execute an immediate follow-up calculation.

○ This revalidation occurs within the same operational window and serves to confirm whether the detected anomaly was due to transient data collection issues or represents a persistent market condition requiring human review.

○ A single-trigger protection mechanism prevents infinite revalidation loops. The marker file is checked prior to each trigger attempt, ensuring that automated re-runs occur at most once per operational cycle.

● **Rationale:** This dual-layer approach (rejection + revalidation) provides robust protection against both systematic data errors and opportunistic attempts to manipulate the index through temporary website alterations or API response injection.

§**8.4.2 Data Quality and Validation Safeguards**

Multiple programmatic checks are applied throughout the data processing pipeline to detect and mitigate data quality issues before they can compromise the final index calculation.

● **NaN and Null Value Poisoning Prevention:**

○ Every arithmetic operation in the weighting and normalization calculations is preceded by a validation check for NaN (Not a Number), None, and zero values.

○ Rather than allowing invalid data to propagate through the calculation pipeline—which would result in a corrupted final index—providers with missing or invalid price data are excluded entirely from the weighted summation for that calculation cycle. Their assigned weights are redistributed proportionally across the remaining providers within the same category (Hyperscaler or Non-Hyperscaler) to preserve the target 60/40 categorical allocation.

○ This approach ensures that partial data collection failures do not result in total index calculation failures, maintaining service continuity even when individual providers' websites or APIs are temporarily unavailable.

● **Statistical Outlier Detection and Filtering:**

○ Prior to index calculation, the normalized price dataset is subjected to an automated outlier detection algorithm using the Interquartile Range (IQR) method. Prices falling outside of Q1 - 2.5×IQR or Q3 + 2.5×IQR are flagged as statistical outliers.

○ The 2.5× multiplier represents a more aggressive filtering threshold than the standard 1.5× used in conventional statistical analysis. This adjustment was calibrated specifically for the H100 market, which exhibits a wider natural price variance due to the heterogeneity of service offerings (e.g., spot vs. reserved, bare-metal vs. virtualized).

○ **Critical Exception:** Hyperscaler prices are explicitly protected from outlier filtering. This design decision reflects the fact that hyperscalers often exhibit pricing structures that differ systematically from the broader market due to their scale, infrastructure amortization models, and enterprise discount structures. Filtering these values would introduce systematic bias into the index.

○ All excluded outliers are logged with their original prices and exclusion rationale, enabling post-hoc analysis of whether the filtering was appropriate or overly aggressive.

● **Price Range Validation:**

○ All finalized prices are checked against hard-coded validity ranges prior to publication or blockchain submission. Prices must satisfy: 0 < Price < $100/hour.

○ Prices of exactly $0 or negative values trigger an immediate calculation abort and invocation of the zero-price contingency protocol (detailed in §8.4.3).

○ Prices exceeding $100/hour generate a warning alert but do not automatically abort the process, as certain specialized or high-availability H100 configurations may legitimately exceed this threshold. The warning prompts manual review before publication.

§**8.4.3 Multi-Level Fallback Mechanisms for Critical Failures**

The methodology incorporates a hierarchical series of fallback protocols that activate when primary calculation methods fail or produce invalid results. These mechanisms are designed to maintain index availability even under severe data collection outages.

● **Zero or Invalid Price Contingency:**

○ If the primary weighted calculation produces a result of zero, NaN, or None—indicating a catastrophic failure of the data collection pipeline—the system automatically retrieves the most recent valid index price from the persistent historical database (gpu\_index\_history.csv).

○ This historical price is used as the published index value for the current period, and the source is tagged as carry\_forward\_prev in the provenance record.

○ This fallback ensures that downstream consumers of the index (e.g., smart contracts, trading systems, financial derivatives) continue to receive valid price feeds even during temporary infrastructure failures.

● **Hyperscaler Price Source Hierarchy:**

○ Hyperscaler pricing follows a three-tier fallback cascade to maximize data availability:

1\. **Primary Source:** Real-time scraped price from the provider's official pricing page, retrieved during the current calculation cycle.

2\. **Secondary Source (website\_price):** A manually curated public list price, typically sourced from the provider's official documentation or last known reliable scraping result. This value is hardcoded in the configuration and updated quarterly.

3\. **Tertiary Source (research\_price):** A proprietary estimate of the effective enterprise price, derived from industry research, partner disclosures, or reverse-engineered from public financial filings. This represents the discounted price large-scale consumers are believed to achieve.

○ The system attempts each source in sequence until a valid (non-null, non-zero) price is obtained. The selected source is logged for each hyperscaler in each calculation cycle.

○ **Rationale:** Hyperscalers represent 60% of the total index weight, and their pricing is critical to index accuracy. This redundancy ensures that temporary API changes, website redesigns, or anti-scraping measures deployed by these providers do not create catastrophic data gaps.

● **Currency Conversion Fallback Rates:**

○ The pipeline fetches live foreign exchange rates from the Frankfurter API (https://api.frankfurter.app) to convert EUR and INR prices to USD.

○ In the event of API unavailability (network outage, service downtime, rate limiting), the system falls back to hardcoded exchange rates: EUR/USD = 1.08, INR/USD = 0.012.

○ These fallback rates are updated monthly based on 30-day moving averages to ensure they remain reasonably accurate approximations.

○ All currency conversions are logged with the source (live\_api or fallback\_static) and the specific exchange rate applied, enabling retroactive correction if significant exchange rate movements occurred during a fallback period.

§**8.4.4 Infrastructure Resilience and Fault Tolerance**

The operational infrastructure is designed to gracefully degrade under partial failure conditions rather than experiencing catastrophic collapse.

● **Scraper-Level Fault Isolation:**

○ The data collection phase executes individual provider scrapers as independent, isolated processes. The failure of any single scraper (due to website downtime, anti-bot measures, DOM structure changes, etc.) does not halt the execution of subsequent scrapers.

○ Each scraper failure is logged with a timestamp and error message, but the pipeline continues to execute all remaining scrapers. The final index calculation proceeds with whatever subset of provider data was successfully collected.

○ This design ensures that the index can be calculated even if a significant minority of providers are temporarily unreachable, relying on the weight redistribution mechanism (§6 Contingency Plan) to compensate for missing data.

● **Blockchain Update Retry Protocol:**

○ When submitting the calculated index price to the on-chain oracle smart contract, the system employs a retry mechanism with exponential backoff.

○ A maximum of three (3) retry attempts are made for each transaction submission. The retry delay is set at five (5) seconds between attempts.

○ This protocol mitigates transient failures such as RPC node congestion, temporary network partitions, mempool backlogs, or gas price estimation errors.

○ If all three attempts fail, the blockchain update is marked as failed, but the calculated index price is still logged to local storage and backup systems. A manual retry can be initiated, or the next scheduled calculation cycle will attempt the update again.

● **On-Chain Verification Protocol:**

○ Following successful submission of a price update transaction to the blockchain, the system performs a read-back verification. The contract's getPrice() function is called for each updated asset, and the returned value is compared to the intended submission value.

○ Any discrepancy between the intended and stored value triggers an alert and is logged as a verification failure. This check detects issues such as transaction reversion that appeared successful at the RPC level, unexpected contract behavior, or precision loss in the encoding/decoding process.

○ This verification step can be disabled via the \--no-verify flag in production environments where gas cost minimization is prioritized over absolute certainty.

● **Data Artifact Preservation:**

○ All intermediate and final data files (JSON, CSV) are automatically uploaded to a cloud storage artifact repository with a 30-day retention policy.

○ This creates a parallel backup of the entire calculation pipeline's output, independent of the version control system. In the event of repository corruption, accidental commit overwrites, or force-push incidents, the calculation can be reconstructed from these preserved artifacts.

○ Artifacts are indexed by timestamp and calculation run ID, enabling precise historical reconstruction of any published index value.

§**8.4.5 Provenance Tracking and Audit Trail**

Every published index price is accompanied by comprehensive metadata documenting its provenance and the conditions under which it was calculated.

● **Source Attribution:**

○ Each entry in the price history database (gpu\_index\_history.csv) includes a source field indicating the calculation method used:

▪ calculated: Standard weighted calculation from fresh data

▪ carry\_forward\_prev: Carried forward from previous period due to invalid calculation result

▪ fallback\_avg: Derived from historical average (not currently implemented but reserved for future use)

▪ rerun: Result of an automated revalidation triggered by anomaly detection

○ This classification enables downstream consumers to assess the reliability and freshness of each published value.

● **Timestamp and Version Integrity:**

○ All data files are timestamped using ISO 8601 format with UTC timezone to ensure unambiguous temporal ordering.

○ The pipeline execution environment enforces time synchronization via NTP to prevent clock drift from corrupting the temporal sequence of records.

● **Failure Reporting and Alerting:**

○ In the event of a complete pipeline failure (e.g., all scrapers fail, calculation aborts, critical exception), the system automatically generates a failure report (failure\_report.md) documenting:

▪ The timestamp of the failure

▪ The list of files that were successfully generated prior to failure

▪ The execution logs from each pipeline stage

▪ The last known valid index price

○ This report is committed to the version control repository, ensuring that human operators are immediately aware of system degradation even if automated alerting systems fail.

§**8.4.6 Operational Safeguards Against Cascading Failures**

Several design decisions in the pipeline architecture are specifically intended to prevent localized failures from cascading into total system collapse.

● **Provider Name Normalization:**

○ The weighting configuration includes multiple name variants for providers known to use inconsistent branding (e.g., "Voltage Park" vs. "VoltagePark", "Shakti Cloud" vs. "ShaktiCloud").

○ This normalization prevents weight fragmentation, where a single provider's weight is erroneously split across multiple entries due to minor naming inconsistencies in the scraped data.

● **Cluster Pricing Special Case Handling:**

○ Certain providers (particularly hyperscalers) offer H100 compute in multi-GPU instance configurations (e.g., 8×H100 nodes) without clearly indicating whether the listed price is per-instance or per-GPU.

○ The normalization logic includes provider-specific and instance-specific heuristics to detect and correct these ambiguities. For example, Google Cloud A3 instances are known to be 8×GPU clusters, and prices are automatically divided by 8 unless the variant name explicitly indicates "per GPU" pricing.

○ These corrections prevent order-of-magnitude errors in the normalized price dataset that would otherwise corrupt the index.

● **Dry-Run and Testing Mode:**

○ The pipeline supports a \--dry-run flag that executes the entire calculation and validation process without committing results to the database, publishing to external consumers, or submitting blockchain transactions.

○ This mode enables safe testing of pipeline changes, validation of new data sources, and diagnosis of calculation anomalies without risking the integrity of the production index.

§**8.4.7 Design Rationale and Limitations**

The contingency protocols described above are designed to prioritize index availability and continuity over absolute real-time accuracy. This design philosophy reflects the intended use case of the index as a reference rate for financial instruments, where the absence of a published price (e.g., due to pipeline failure) is more disruptive to market participants than the publication of a price that is one calculation period stale.

However, these automated interventions introduce several important considerations:

● **Staleness Risk:** Extended reliance on carry-forward mechanisms (e.g., during a multi-day scraping outage) can result in the published index price becoming decoupled from real-time market conditions. Downstream consumers should monitor the source attribution field to detect prolonged fallback periods.

● **Anomaly Threshold Calibration:** The 50% change threshold for anomaly detection is conservative and designed to minimize false positives. However, in the event of a genuine, rapid market shock (e.g., a sudden supply disruption or new hardware release rendering H100s obsolete), this mechanism could delay the index's response to legitimate market movements. The threshold is reviewed quarterly and may be adjusted based on observed market volatility.

● **Weight Redistribution Bias:** When providers are excluded due to data unavailability, their weights are redistributed proportionally within their category. This redistribution can introduce subtle compositional shifts in the index if outages disproportionately affect providers with specific pricing characteristics (e.g., consistently low-cost providers). Long-term monitoring of exclusion patterns is recommended.

§**9\. Results Synthesis and Benchmark Construction** 

The culmination of the preceding procedures is the synthesis of all processed data into the final H100 Compute Index Price. This section also discusses how this benchmark can be used to construct a functioning compute exchange. 

§**9.1 Construction of the Final Benchmark** 

The process of finalization involves a sequence of well-defined steps: 

1\. **Final Data Aggregation:** The verified, single, normalized per-GPU hourly price for each of the 47 qualified providers is compiled into a final table. 

2\. **Final Weight Calculation:** The final, discount-adjusted revenue weights for each provider are calculated and compiled into a parallel table. 

3\. **Weighted Summation:** The core calculation is performed by multiplying each provider's final price by its final weight and summing the results across all providers. 

4\. **Sanity Checking:** The resulting index price is checked against several benchmarks to ensure its validity. It is compared to the simple average price, the median price, and the previous period's index price. 

5\. **Publication:** The final H100 Compute Index Price is timestamped and published. 

§**10\. Limitations, Assumptions, and Risk Assessment** 

A clear understanding of the methodology's limitations is essential for its proper application. §**10.1 Key Assumptions** 

The calculation of the index relies on several key assumptions. The validity of the index is contingent upon the reasonableness of these assumptions. 

● **\[ASSUMPTION: Accuracy of Third-Party Data\]** The methodology assumes that the revenue and fleet size estimates for private companies are reasonably accurate. 

● **\[ASSUMPTION: Validity of Discount Estimates\]** It is assumed that our proprietary research into hyperscaler discounting yields representative estimates. 

● **\[ASSUMPTION: Performance Normalization Model\]** The performance normalization model assumes that the weighted average of the selected hardware specifications serves as a valid proxy for the overall effective performance of an H100 GPU on typical AI workloads. 

● **\[ASSUMPTION: Market Representation\]** It is assumed that the 47 providers included in  
the final calculation constitute a sufficiently large and diverse sample to be representative of the entire global H100 compute market. 

§**10.2 Limitations** 

● **Spot Market Exclusion:** The current methodology is based primarily on on-demand and committed-use pricing. It does not fully incorporate the highly volatile pricing of interruptible "spot" instances.

● **Lack of Geographic Granularity:** The index is a single global figure. It does not provide separate benchmarks for different geographic regions, which can have significant variations in operational costs and pricing. 

● **Non-Price Factors:** The index is a pure price metric. It does not account for non-price factors that are critical in procurement decisions, such as quality of service, network performance, reliability SLAs, and customer support. 

● **Static Nature:** The index is calculated periodically (e.g., quarterly) and represents

snapshot in time. It does not capture intraday or intra-week price volatility. 

§**10.3 Risk Assessment** 

● **Data Sourcing Risk:** The primary risk is the potential for inaccurate or biased input data, particularly for private companies. A significant error in the revenue estimate of a large non-hyperscaler could materially impact the index. 

● **Model Risk:** The weighting and normalization models may not perfectly capture all market dynamics. A new AI model architecture could emerge that heavily favors a hardware spec not highly weighted in our model. 

● **Market Manipulation Risk:** As the index gains prominence, there is a theoretical risk that a provider could alter its public pricing in an attempt to influence the index. This is mitigated by the broad base of 47 providers and the heavy weighting on revenue, which cannot be easily manipulated.

§**11\. Appendix A: Source Data Tables** 

**Table A1: H100 Hardware Specification Normalization Weights** 

| Hardware Specification  | Assigned Weight |
| :---- | :---- |
| FP16 TFLOPS  | 0.155983 |
| FP64 TFLOPS  | 0.155958 |
| CUDA Cores  | 0.144435 |
| Tensor Cores  | 0.144435 |
| VRAM (GB)  | 0.140570 |
| Memory Bandwidth (GB/s)  | 0.138890 |
| L2 Cache (MB)  | 0.119730 |

