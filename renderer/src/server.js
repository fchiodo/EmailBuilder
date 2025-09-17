const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const mjml = require('mjml');
require('dotenv').config();

const { generateMJML } = require('./templates/generator');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:8000'],
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'renderer', version: '1.0.0' });
});

// Render template endpoint
app.post('/render', async (req, res) => {
  try {
    const { locale, templateType, subject, preheader, blocks } = req.body;

    if (!templateType || !blocks) {
      return res.status(400).json({
        error: 'Missing required fields: templateType, blocks'
      });
    }

    // Generate MJML from template
    const mjmlContent = generateMJML({
      locale,
      templateType,
      subject,
      preheader,
      blocks
    });

    // Compile MJML to HTML
    const { html, errors } = mjml(mjmlContent, {
      validationLevel: 'soft',
      fonts: {
        'Open Sans': 'https://fonts.googleapis.com/css?family=Open+Sans:300,400,500,700',
        'Roboto': 'https://fonts.googleapis.com/css?family=Roboto:300,400,500,700'
      }
    });

    if (errors && errors.length > 0) {
      console.warn('MJML compilation warnings:', errors);
    }

    res.json({
      mjml: mjmlContent,
      html: html,
      warnings: errors || []
    });

  } catch (error) {
    console.error('Render error:', error);
    res.status(500).json({
      error: 'Failed to render template',
      message: error.message
    });
  }
});

// Direct MJML compilation endpoint
app.post('/compile', async (req, res) => {
  try {
    const { mjml: mjmlContent } = req.body;

    if (!mjmlContent) {
      return res.status(400).json({ error: 'Missing MJML content' });
    }

    const { html, errors } = mjml(mjmlContent, {
      validationLevel: 'soft'
    });

    res.json({
      html: html,
      warnings: errors || []
    });

  } catch (error) {
    console.error('Compilation error:', error);
    res.status(500).json({
      error: 'Failed to compile MJML',
      message: error.message
    });
  }
});

// Error handling middleware
app.use((error, req, res, next) => {
  console.error('Unhandled error:', error);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  console.log(`🎨 MJML Renderer Service running on port ${PORT}`);
  console.log(`📧 Ready to render emails at http://localhost:${PORT}`);
});