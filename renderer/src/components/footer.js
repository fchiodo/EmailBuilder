/**
 * Footer component for email templates
 * @param {Object} block - Footer block data
 * @param {Object} tokens - Design tokens
 * @returns {string} MJML component
 */
function footerComponent(block, tokens) {
  const { legal, preferencesUrl, unsubscribeUrl } = block;

  return `
    <mj-section background-color="${tokens.colors.secondary}" padding-top="${tokens.spacing.xxl}">
      <mj-column>
        <mj-divider border-color="${tokens.colors.textSecondary}" border-width="1px" padding-bottom="${tokens.spacing.lg}" />

        <mj-text
          align="center"
          font-size="12px"
          color="${tokens.colors.textSecondary}"
          padding-bottom="${tokens.spacing.md}"
        >
          ${legal}
        </mj-text>

        <mj-text
          align="center"
          font-size="12px"
          color="${tokens.colors.textSecondary}"
          padding-bottom="${tokens.spacing.lg}"
        >
          <a href="${preferencesUrl}" style="color: ${tokens.colors.textSecondary}; text-decoration: underline;">
            Gestisci preferenze
          </a>
          &nbsp;|&nbsp;
          <a href="${unsubscribeUrl}" style="color: ${tokens.colors.textSecondary}; text-decoration: underline;">
            Annulla iscrizione
          </a>
        </mj-text>
      </mj-column>
    </mj-section>
  `.trim();
}

module.exports = { footerComponent };