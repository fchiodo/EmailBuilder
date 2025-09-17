export type TemplateType = 'post_purchase' | 'cart_abandon' | 'order_confirmation';

export interface TemplateRequest {
  templateType: TemplateType;
  locale: string;
  skus: string[];
  customerContext?: Record<string, any>;
}

export interface TemplateBlock {
  type: 'hero' | 'items' | 'recommendations' | 'footer';
}

export interface HeroBlock extends TemplateBlock {
  type: 'hero';
  headline: string;
  subcopy: string;
  imageUrl: string;
}

export interface ItemsBlock extends TemplateBlock {
  type: 'items';
  title: string;
  items: Array<{
    sku: string;
    name: string;
    price: string;
    imageUrl: string;
    url: string;
  }>;
}

export interface RecommendationsBlock extends TemplateBlock {
  type: 'recommendations';
  title: string;
  items: Array<{
    sku: string;
    name: string;
    price: string;
    imageUrl: string;
    url: string;
  }>;
}

export interface FooterBlock extends TemplateBlock {
  type: 'footer';
  legal: string;
  preferencesUrl: string;
  unsubscribeUrl: string;
}

export interface TemplateSchema {
  locale: string;
  templateType: TemplateType;
  subject: string;
  preheader: string;
  blocks: Array<HeroBlock | ItemsBlock | RecommendationsBlock | FooterBlock>;
}

export interface GenerateResponse {
  jsonTemplate: TemplateSchema;
  mjml: string;
  html: string;
  tokensVersion: string;
}