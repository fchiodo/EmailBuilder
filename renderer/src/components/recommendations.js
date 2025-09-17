/**
 * Recommendations component for suggested products
 * @param {Object} block - Recommendations block data
 * @param {Object} tokens - Design tokens
 * @returns {string} MJML component
 */
function recommendationsComponent(block, tokens) {
  const { title, items } = block;

  if (!items || items.length === 0) {
    return '';
  }

  const itemsMarkup = items.slice(0, 3).map(item => `
    <mj-column width="33.33%" padding="${tokens.spacing.sm}">
      <mj-image
        src="${item.imageUrl}"
        alt="${item.name}"
        align="center"
        border-radius="${tokens.radius.card}"
        padding-bottom="${tokens.spacing.sm}"
        href="${item.url}"
      />

      <mj-text
        align="center"
        font-size="14px"
        font-weight="600"
        color="${tokens.colors.text}"
        padding-bottom="${tokens.spacing.xs}"
      >
        ${item.name}
      </mj-text>

      <mj-text
        align="center"
        font-size="${tokens.fonts.body.size}"
        color="${tokens.colors.primary}"
        font-weight="700"
        padding-bottom="${tokens.spacing.sm}"
      >
        ${item.price}
      </mj-text>

      <mj-button
        href="${item.url}"
        background-color="transparent"
        color="${tokens.colors.primary}"
        font-size="14px"
        padding="${tokens.spacing.xs} ${tokens.spacing.md}"
        border="${tokens.colors.primary} 1px solid"
        border-radius="${tokens.radius.button}"
      >
        Scopri
      </mj-button>
    </mj-column>
  `).join('');

  return `
    <mj-section background-color="${tokens.colors.surface}" css-class="section-spacing">
      <mj-column>
        <mj-text
          align="center"
          font-size="${tokens.fonts.heading.size}"
          font-weight="${tokens.fonts.heading.weight}"
          color="${tokens.colors.text}"
          padding-bottom="${tokens.spacing.lg}"
        >
          ${title}
        </mj-text>
      </mj-column>
    </mj-section>

    <mj-section background-color="${tokens.colors.surface}">
      ${itemsMarkup}
    </mj-section>
  `.trim();
}

module.exports = { recommendationsComponent };