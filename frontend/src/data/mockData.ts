import type {
  Asset, AiOutlook, RiskItem, MarketPulse, DashboardMetric,
  DisclosureMeta, DisclosureCard, FinancialRow,
  NewsArticle, SentimentDivergenceItem, MacroContextItem,
  ChatDocument, ChatMessage, NavPage,
} from '../types';

export const NAV_PAGES: NavPage[] = [
  { key: 'dashboard',   name: 'Executive Dashboard', icon: '⊞' },
  { key: 'disclosures', name: '10-K Disclosures',    icon: '📄' },
  { key: 'sentiment',   name: 'Market Sentiment',    icon: '📈' },
  { key: 'chat',        name: 'Talk to Report',      icon: '💬' },
];

export const ASSETS: Record<string, string> = {
  AAPL:  '↑ 1.24%',
  MSFT:  '↓ 0.45%',
  TSLA:  '↑ 2.10%',
  GOOGL: '↑ 0.82%',
};

export const ASSET_DATA: Asset = {
  name: 'Apple Inc.',
  ticker: 'AAPL',
  exchange: 'NasdaqGS',
  dataType: 'Real-time Data',
  price: 185.00,
  changePct: 1.2,
  changeDirection: 'up',
};

export const AI_OUTLOOK: AiOutlook = {
  title: 'AI Overall Outlook',
  subtitle: 'Cross-referencing 10-K Filings with Global Macro Sentiment',
  quote:
    'While Apple highlights robust services growth and strong hardware margins ' +
    'in their 10-K, external market sentiment remains cautious regarding ' +
    'geopolitical supply chain risks and antitrust regulatory scrutiny in key markets.',
  tags: ['Regulatory Review', 'Supply Chain Resilience', 'Margin Expansion'],
};

export const DASHBOARD_TOP_RISKS: RiskItem[] = [
  {
    title: 'Supply Chain Dependency',
    description:
      'Concentration of manufacturing in specific regions poses risk to assembly timelines and cost structure.',
    icon: '⚠️',
  },
  {
    title: 'Regulatory Pressure',
    description:
      'Increasing scrutiny from global competition authorities regarding App Store ecosystem and hardware dominance.',
    icon: '⚖️',
  },
  {
    title: 'Geopolitical Conflict',
    description:
      'International trade tensions impacting consumer demand and cross-border data transfer protocols.',
    icon: '🌐',
  },
];

export const MARKET_SENTIMENT_PULSE: MarketPulse = {
  confidenceIndex: 0.65,
  label: 'Bullish',
  confidenceTier: 'Top Tier Confidence',
  description:
    'Based on 1.2M social mentions, analyst upgrades, and institutional flow data over the last 48 hours.',
};

export const DASHBOARD_METRICS: DashboardMetric[] = [
  { label: 'INSTITUTIONAL HEAT', value: 'High Activity',  icon: '👁' },
  { label: 'EXECUTION VELOCITY', value: 'Accelerated',    icon: '✅' },
  { label: 'RISK VOLATILITY',    value: 'Moderate (+2%)', icon: '📊' },
];

// ─── Disclosures ─────────────────────────────────────────────────────────────

export const DISCLOSURE_META: DisclosureMeta = {
  title: 'Apple Inc. (AAPL)',
  subtitle: 'Securities and Exchange Commission, Washington, D.C. 20549',
  reportLabel: 'FY 2023 Annual Report',
};

export const DISCLOSURE_KEY_RISKS: DisclosureCard[] = [
  {
    title: 'Supply Chain Dependency',
    pageRef: 'Page 12, Item 1A',
    description:
      'Significant reliance on outsourced manufacturing partners, primarily located in Asia, poses logistical and geopolitical risks. Any disruption in these regions could materially impact the production and delivery of key hardware products.',
    impact: 'HIGH IMPACT',
    impactLevel: 'high',
    icon: '⚠️',
  },
  {
    title: 'Regulatory Compliance',
    pageRef: 'Page 14, Item 1A',
    description:
      'The company is subject to complex and evolving laws and regulations worldwide. Changes in antitrust, privacy, and environmental laws could increase operating costs or require changes to business practices.',
    impact: 'MEDIUM IMPACT',
    impactLevel: 'medium',
    icon: '⚖️',
  },
  {
    title: 'Foreign Exchange Volatility',
    pageRef: 'Page 17, Item 1A',
    description:
      'Fluctuations in the value of the U.S. Dollar against other currencies can significantly affect reported revenue and gross margins, given that a large portion of net sales is generated outside the United States.',
    impact: 'LOW IMPACT',
    impactLevel: 'low',
    icon: '💱',
  },
  {
    title: 'Cybersecurity Threats',
    pageRef: 'Page 22, Item 1A',
    description:
      'Potential security breaches or system failures could compromise the confidentiality of customer data, leading to reputational damage, legal liability, and loss of competitive advantage.',
    impact: 'HIGH IMPACT',
    impactLevel: 'high',
    icon: '🛡️',
  },
];

export const DISCLOSURE_GROWTH_DRIVERS: DisclosureCard[] = [
  {
    title: 'Services Revenue Expansion',
    pageRef: 'Page 5, Item 1',
    description:
      'Services segment including App Store, Apple Music, iCloud, and Apple Pay continues to grow at double-digit rates, providing higher-margin recurring revenue streams that reduce hardware-cycle dependency.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '📱',
  },
  {
    title: 'Emerging Market Penetration',
    pageRef: 'Page 8, Item 1',
    description:
      'Expanding presence in India and Southeast Asia through new retail stores, localised products, and financing options is driving volume growth in high-potential markets.',
    impact: 'MEDIUM IMPACT',
    impactLevel: 'positive_medium',
    icon: '🌏',
  },
  {
    title: 'Vision Pro Platform',
    pageRef: 'Page 11, Item 1',
    description:
      'Launch of spatial computing platform creates new ecosystem opportunities for enterprise and developer adoption, establishing an early-mover advantage in the mixed-reality category.',
    impact: 'MEDIUM IMPACT',
    impactLevel: 'positive_medium',
    icon: '🥽',
  },
  {
    title: 'AI Feature Integration',
    pageRef: 'Page 15, Item 1',
    description:
      'On-device intelligence and Apple Intelligence features are differentiating the hardware ecosystem and driving upgrade cycles among the over two billion active device installed base.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '🤖',
  },
];

export const DISCLOSURE_STRATEGIC_FOCUS: DisclosureCard[] = [
  {
    title: 'Platform Ecosystem Lock-In',
    pageRef: 'Page 9, Item 1',
    description:
      'Deep integration between hardware, software, and services creates a stickiness effect across the Apple ecosystem, reducing churn and increasing lifetime customer value.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '🔗',
  },
  {
    title: 'R&D Investment in Silicon',
    pageRef: 'Page 18, Item 1',
    description:
      'Continued investment in proprietary chip design (M-series, A-series) creates performance and efficiency advantages that differentiate Apple products from commodity hardware competitors.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '🔬',
  },
  {
    title: 'Privacy as Differentiator',
    pageRef: 'Page 21, Item 1',
    description:
      'Positioning privacy as a core product value resonates with premium consumers and enterprise buyers, supporting pricing power and brand loyalty in competitive markets.',
    impact: 'MEDIUM IMPACT',
    impactLevel: 'positive_medium',
    icon: '🔒',
  },
  {
    title: 'Retail Experience Expansion',
    pageRef: 'Page 25, Item 1',
    description:
      "Apple's owned retail footprint provides a direct-to-consumer channel that controls brand experience, reduces third-party margin dependency, and supports premium positioning globally.",
    impact: 'MEDIUM IMPACT',
    impactLevel: 'positive_medium',
    icon: '🏪',
  },
];

export const DISCLOSURE_FINANCIAL_TRENDS: DisclosureCard[] = [
  {
    title: 'Services Margin Expansion',
    pageRef: 'Page 30, Item 6',
    description:
      'Services gross margin of 70.8% in FY2023 vs 72.4% in FY2022, reflecting ongoing investment in content and infrastructure while sustaining significantly higher margins than the Products segment.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '📈',
  },
  {
    title: 'Share Buyback Programme',
    pageRef: 'Page 35, Item 7',
    description:
      'Apple returned over $89B to shareholders through buybacks and dividends in FY2023, reducing diluted share count and supporting EPS growth despite flat net income.',
    impact: 'HIGH IMPACT',
    impactLevel: 'positive_high',
    icon: '💰',
  },
  {
    title: 'Revenue Concentration Risk',
    pageRef: 'Page 38, Item 7',
    description:
      'iPhone represents 52% of total net sales, creating dependency on a single product category and making overall revenue sensitive to upgrade cycle timing and competitive dynamics.',
    impact: 'HIGH IMPACT',
    impactLevel: 'high',
    icon: '⚠️',
  },
  {
    title: 'Operating Expense Discipline',
    pageRef: 'Page 42, Item 7',
    description:
      'Operating expenses grew only 5.4% YoY versus revenue decline of 2.8%, demonstrating cost discipline and protecting operating margin contraction in a challenging macro environment.',
    impact: 'MEDIUM IMPACT',
    impactLevel: 'positive_medium',
    icon: '📉',
  },
];

export const FINANCIAL_SNAPSHOT_HEADERS = ['METRIC (USD IN MILLIONS)', 'FY 2023', 'FY 2022', 'CHANGE %'];
export const FINANCIAL_SNAPSHOT_ROWS: FinancialRow[] = [
  { metric: 'Total Net Sales (Revenue)',  fy2023: '$383,285', fy2022: '$394,328', change: '-2.8%'  },
  { metric: 'Net Income',                 fy2023: '$96,995',  fy2022: '$99,803',  change: '-2.8%'  },
  { metric: 'Operating Margin',           fy2023: '29.8%',    fy2022: '30.3%',    change: '-50 bps' },
  { metric: 'Earnings Per Share (Diluted)',fy2023: '$6.13',    fy2022: '$6.11',    change: '+0.3%'  },
  { metric: 'Free Cash Flow',             fy2023: '$99,584',  fy2022: '$111,443', change: '-10.6%' },
];

// ─── Sentiment ────────────────────────────────────────────────────────────────

export const NEWS_ARTICLES: NewsArticle[] = [
  {
    source: 'BLOOMBERG',
    time: '2H AGO',
    sentiment: 'BULLISH',
    title: 'iPhone demand stabilises in emerging markets as premiumisation trend accelerates',
    description:
      'Supply chain data suggests a 4% increase in ASP for the Indian market, offsetting conservative volumes in domestic sectors.',
  },
  {
    source: 'REUTERS',
    time: '4H AGO',
    sentiment: 'NEUTRAL',
    title: 'Quarterly services guidance remains unchanged ahead of earnings call',
    description:
      "Analysts maintain 'Hold' rating as hardware refresh cycles reach plateau in North American markets.",
  },
  {
    source: 'WSJ',
    time: '6H AGO',
    sentiment: 'BEARISH',
    title: 'Antitrust probe expands into App Store payment processing fees',
    description:
      'EU regulators signal potential for multi-billion euro fine following formal complaints from competing software ecosystems.',
  },
  {
    source: 'TECHCRUNCH',
    time: '8H AGO',
    sentiment: 'BULLISH',
    title: 'AI Integration roadmap reveals significant efficiency gains for internal Ops',
    description:
      'Leak of internal roadmap shows integration of LLMs across customer support and hardware design workflows.',
  },
  {
    source: 'CNBC',
    time: '1D AGO',
    sentiment: 'NEUTRAL',
    title: 'New product launch event confirmed for mid-September timeframe',
    description:
      "Invitations sent for 'Glowtime' event, expected to feature iterative updates to core product lines.",
  },
];

export const AI_THEMES: string[] = [
  'Services Growth', 'Antitrust', 'AI Integration', 'FSD Update', 'Margin Pressure',
];

export const SENTIMENT_DIVERGENCE: Record<string, SentimentDivergenceItem> = {
  institutional: { label: 'Institutional Focus', value: 78, direction: 'Positive' },
  social:        { label: 'Social Sentiment',    value: 32, direction: 'Negative' },
};

export const MACRO_CONTEXT: MacroContextItem[] = [
  { label: 'S&P 500',   value: '+0.42%' },
  { label: 'NASDAQ',    value: '-0.12%' },
  { label: '10Y Yield', value: '4.21%'  },
];

// ─── Chat ─────────────────────────────────────────────────────────────────────

export const CHAT_DOCUMENT: ChatDocument = {
  title: 'Apple Inc. 2023 Annual Report (10-K)',
  description: 'Synthesising risk factors, liquidity, and segment data across 114 pages.',
  status: 'ANALYSIS READY',
};

export const CHAT_MESSAGES: ChatMessage[] = [
  {
    role: 'assistant',
    content: 'Hello! I have analysed Apple\'s latest 10-K. What would you like to know?',
    suggestions: ['Summarize Risks', 'Revenue by Segment', 'R&D Spend Analysis'],
  },
  {
    role: 'user',
    content: 'Can you summarise the primary risk factors listed?',
  },
  {
    role: 'assistant',
    content:
      'Based on the **Item 1A** section of the 10-K, Apple identifies several critical risks. I\'ve categorised the most significant ones for you:',
    cards: [
      { title: 'SUPPLY CHAIN',  description: 'Dependency on third-party manufacturing and components primarily in China.' },
      { title: 'MACROECONOMIC', description: 'Exposure to global economic conditions and currency fluctuations.' },
      { title: 'REGULATION',    description: 'Increasing antitrust scrutiny regarding the App Store and digital services.' },
      { title: 'INNOVATION',    description: 'Intense competition and pressure to release new products frequently.' },
    ],
    citations: 'Citations: Page 14–22',
  },
];
