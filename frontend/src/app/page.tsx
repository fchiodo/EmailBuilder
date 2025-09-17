'use client';

import { useState } from 'react';
import { TemplateType, TemplateRequest, GenerateResponse } from '@/types/template';

export default function Home() {
  const [templateType, setTemplateType] = useState<TemplateType>('cart_abandon');
  const [locale, setLocale] = useState('it-IT');
  const [skus, setSkus] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const request: TemplateRequest = {
        templateType,
        locale,
        skus: skus.split(',').map(s => s.trim()).filter(Boolean),
      };

      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data);
      }
    } catch (error) {
      console.error('Generation failed:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">EmailBuilder</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Controls Panel */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Template Configuration</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Template Type
                </label>
                <select
                  value={templateType}
                  onChange={(e) => setTemplateType(e.target.value as TemplateType)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="cart_abandon">Cart Abandonment</option>
                  <option value="post_purchase">Post Purchase</option>
                  <option value="order_confirmation">Order Confirmation</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Locale
                </label>
                <select
                  value={locale}
                  onChange={(e) => setLocale(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  <option value="it-IT">Italian</option>
                  <option value="en-US">English</option>
                  <option value="fr-FR">French</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  SKUs (comma-separated)
                </label>
                <textarea
                  value={skus}
                  onChange={(e) => setSkus(e.target.value)}
                  placeholder="SKU001, SKU002, SKU003..."
                  className="w-full border border-gray-300 rounded-md px-3 py-2 h-20"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="w-full bg-blue-600 text-white rounded-md px-4 py-2 font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {isGenerating ? 'Generating...' : 'Generate Email'}
              </button>
            </div>
          </div>

          {/* Preview Panel */}
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200 px-6 py-4">
              <h2 className="text-xl font-semibold">Preview</h2>
            </div>

            <div className="p-6">
              {result ? (
                <div className="space-y-4">
                  <div>
                    <strong>Subject:</strong> {result.jsonTemplate.subject}
                  </div>
                  <div>
                    <strong>Preheader:</strong> {result.jsonTemplate.preheader}
                  </div>

                  <div className="border rounded-lg overflow-hidden">
                    <iframe
                      srcDoc={result.html}
                      className="w-full h-96"
                      title="Email Preview"
                    />
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-12">
                  Generate an email to see the preview
                </div>
              )}
            </div>
          </div>
        </div>

        {/* JSON/MJML Panels */}
        {result && (
          <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white rounded-lg shadow">
              <div className="border-b border-gray-200 px-6 py-4">
                <h3 className="text-lg font-semibold">JSON Template</h3>
              </div>
              <div className="p-6">
                <pre className="text-sm overflow-auto h-64 bg-gray-50 p-4 rounded">
                  {JSON.stringify(result.jsonTemplate, null, 2)}
                </pre>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow">
              <div className="border-b border-gray-200 px-6 py-4">
                <h3 className="text-lg font-semibold">MJML</h3>
              </div>
              <div className="p-6">
                <pre className="text-sm overflow-auto h-64 bg-gray-50 p-4 rounded">
                  {result.mjml}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
