const { heroComponent } = require('../components/hero');
const { itemsComponent } = require('../components/items');
const { recommendationsComponent } = require('../components/recommendations');
const { footerComponent } = require('../components/footer');

/**
 * Generate MJML content from template schema
 * @param {Object} template - Template schema with blocks
 * @returns {string} MJML content
 */
function generateMJML(template) {
  const { locale, templateType, subject, preheader, blocks } = template;

  // Load design tokens based on template type
  const tokens = loadDesignTokens(templateType);

  const mjmlBlocks = blocks.map(block => {
    switch (block.type) {
      case 'hero':
        return heroComponent(block, tokens);
      case 'items':
        return itemsComponent(block, tokens);
      case 'recommendations':
        return recommendationsComponent(block, tokens);
      case 'footer':
        return footerComponent(block, tokens);
      default:
        console.warn(`Unknown block type: ${block.type}`);
        return '';
    }
  }).join('\n');

  return `
<mjml>
  <mj-head>
    <mj-title>${subject}</mj-title>
    <mj-preview>${preheader}</mj-preview>

    <mj-attributes>
      <mj-text color="${tokens.colors.text}" font-family="${tokens.fonts.body.family}" font-size="${tokens.fonts.body.size}" line-height="${tokens.fonts.body.lineHeight}" />
      <mj-button background-color="${tokens.colors.primary}" color="${tokens.colors.onPrimary}" font-family="${tokens.fonts.body.family}" border-radius="${tokens.radius.button}" />
    </mj-attributes>

    <mj-style>
      .content-padding { padding: ${tokens.spacing.md} ${tokens.spacing.lg}; }
      .section-spacing { padding-top: ${tokens.spacing.xl}; padding-bottom: ${tokens.spacing.xl}; }
    </mj-style>
  </mj-head>

  <mj-body background-color="${tokens.colors.background}">
    ${mjmlBlocks}
  </mj-body>
</mjml>`.trim();
}

/**
 * Load design tokens for a specific template type
 * @param {string} templateType
 * @returns {Object} Design tokens
 */
function loadDesignTokens(templateType) {
  // In production, this would load from ../tokens/{templateType}.json
  // For now, return default tokens
  const defaultTokens = {
    colors: {
      primary: '#2563eb',
      onPrimary: '#ffffff',
      secondary: '#64748b',
      background: '#f8fafc',
      surface: '#ffffff',
      text: '#1e293b',
      textSecondary: '#64748b'
    },
    fonts: {
      heading: {
        family: 'Arial, sans-serif',
        size: '24px',
        weight: '700',
        lineHeight: '1.2'
      },
      body: {
        family: 'Arial, sans-serif',
        size: '16px',
        weight: '400',
        lineHeight: '1.5'
      }
    },
    spacing: {
      xs: '4px',
      sm: '8px',
      md: '16px',
      lg: '24px',
      xl: '32px',
      xxl: '48px'
    },
    radius: {
      button: '6px',
      card: '8px'
    }
  };

  // Template-specific overrides
  const templateOverrides = {
    cart_abandon: {
      colors: {
        ...defaultTokens.colors,
        primary: '#dc2626' // Red for urgency
      }
    },
    post_purchase: {
      colors: {
        ...defaultTokens.colors,
        primary: '#059669' // Green for success
      }
    },
    order_confirmation: {
      colors: {
        ...defaultTokens.colors,
        primary: '#2563eb' // Blue for trust
      }
    }
  };

  return {
    ...defaultTokens,
    ...(templateOverrides[templateType] || {})
  };
}

module.exports = { generateMJML };