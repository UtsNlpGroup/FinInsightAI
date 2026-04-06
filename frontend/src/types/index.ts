export type PageKey = 'dashboard' | 'disclosures' | 'sentiment' | 'chat';

export interface NavPage {
  key: PageKey;
  name: string;
  icon: string;
}

export interface Asset {
  name: string;
  ticker: string;
  exchange: string;
  dataType: string;
  price: number;
  changePct: number;
  changeDirection: 'up' | 'down';
}

export interface AiOutlook {
  title: string;
  subtitle: string;
  quote: string;
  tags: string[];
}

export interface RiskItem {
  title: string;
  description: string;
  icon: string;
}

export interface MarketPulse {
  confidenceIndex: number;
  label: string;
  confidenceTier: string;
  description: string;
}

export interface DashboardMetric {
  label: string;
  value: string;
  icon: string;
}

export interface DisclosureMeta {
  title: string;
  subtitle: string;
  reportLabel: string;
}

export interface DisclosureCard {
  title: string;
  pageRef: string;
  description: string;
  impact: string;
  impactLevel: 'high' | 'medium' | 'low' | 'positive_high' | 'positive_medium';
  icon: string;
}

export interface FinancialRow {
  metric: string;
  fy2023: string;
  fy2022: string;
  change: string;
}

export interface NewsArticle {
  source: string;
  time: string;
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL';
  title: string;
  description: string;
}

export interface SentimentDivergenceItem {
  label: string;
  value: number;
  direction: string;
}

export interface MacroContextItem {
  label: string;
  value: string;
}

export interface ChatCard {
  title: string;
  description: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
  cards?: ChatCard[];
  citations?: string;
}

export interface ChatDocument {
  title: string;
  description: string;
  status: string;
}
