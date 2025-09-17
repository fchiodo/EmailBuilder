/**
 * Hero component for email templates
 * @param {Object} block - Hero block data
 * @param {Object} tokens - Design tokens
 * @returns {string} MJML component
 */
function heroComponent(block, tokens) {
  const { headline, subcopy, imageUrl } = block;

  return `
    <mj-section background-color="${tokens.colors.surface}" css-class="section-spacing">
      <mj-column>
        ${imageUrl ? `
        <mj-image
          src="${imageUrl}"
          alt="${headline}"
          align="center"
          border-radius="${tokens.radius.card}"
          padding-bottom="${tokens.spacing.lg}"
        />
        ` : ''}

        <mj-text
          align="center"
          font-size="${tokens.fonts.heading.size}"
          font-weight="${tokens.fonts.heading.weight}"
          line-height="${tokens.fonts.heading.lineHeight}"
          color="${tokens.colors.text}"
          padding-bottom="${tokens.spacing.md}"
        >
          ${headline}
        </mj-text>

        ${subcopy ? `
        <mj-text
          align="center"
          font-size="${tokens.fonts.body.size}"
          color="${tokens.colors.textSecondary}"
          padding-bottom="${tokens.spacing.lg}"
        >
          ${subcopy}
        </mj-text>
        ` : ''}
      </mj-column>
    </mj-section>
  `.trim();
}

module.exports = { heroComponent };