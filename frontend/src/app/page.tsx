'use client';

import { useState, useRef, useEffect } from 'react';
import { TemplateType, TemplateRequest, GenerateResponse } from '@/types/template';
import MultiAgentLoader from '@/components/MultiAgentLoader';

export default function Home() {
  const [templateType, setTemplateType] = useState<TemplateType>('cart_abandon');
  const [locale, setLocale] = useState('it-IT');
  const [skus, setSkus] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'preview' | 'json' | 'mjml'>('preview');
  const [uploadedTemplateId, setUploadedTemplateId] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [showMultiAgentLoader, setShowMultiAgentLoader] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize iframe to fit content
  const resizeIframe = () => {
    const iframe = iframeRef.current;
    if (iframe) {
      try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        if (iframeDoc) {
          const body = iframeDoc.body;
          const html = iframeDoc.documentElement;
          const height = Math.max(
            body?.scrollHeight || 0,
            body?.offsetHeight || 0,
            html?.clientHeight || 0,
            html?.scrollHeight || 0,
            html?.offsetHeight || 0
          );
          iframe.style.height = Math.max(height, 600) + 'px';
        }
      } catch (error) {
        // Cross-origin restrictions, fallback to fixed height
        iframe.style.height = '800px';
      }
    }
  };

  useEffect(() => {
    if (result && activeTab === 'preview') {
      // Small delay to ensure iframe content is loaded
      const timer = setTimeout(resizeIframe, 100);
      return () => clearTimeout(timer);
    }
  }, [result, activeTab]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setShowMultiAgentLoader(true);
    setGenerationError(null);
    setResult(null);
  };

  const handleGenerationComplete = (result: any) => {
    // Convert result to expected format
    const formattedResult: GenerateResponse = {
      jsonTemplate: {
        locale: result.template_json.locale,
        templateType: result.template_json.templateType,
        subject: result.template_json.subject,
        preheader: result.template_json.preheader,
        blocks: result.template_json.blocks
      },
      mjml: result.mjml,
      html: result.html,
      tokensVersion: result.tokens_version
    };

    setResult(formattedResult);
    setActiveTab('preview');
    setShowMultiAgentLoader(false);
    setIsGenerating(false);
  };

  const handleGenerationError = (error: string) => {
    setGenerationError(error);
    setShowMultiAgentLoader(false);
    setIsGenerating(false);
  };

  const getCurrentTemplateRequest = (): TemplateRequest => {
    return {
      templateType,
      locale,
      skus: skus.split(',').map(s => s.trim()).filter(Boolean),
      customTemplateId: uploadedTemplateId || undefined,
      brandGuidelineFile: uploadedTemplateId || undefined,
      category: 'general'
    };
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload-template', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setUploadedTemplateId(data.fileId);
        setUploadedFileName(data.filename);
      } else {
        console.error('Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const clearUploadedTemplate = () => {
    setUploadedTemplateId(null);
    setUploadedFileName(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const templateOptions = [
    { value: 'cart_abandon', label: '🛒 Cart Abandonment', desc: 'Re-engage customers who left items' },
    { value: 'post_purchase', label: '✅ Post Purchase', desc: 'Thank customers and suggest more' },
    { value: 'order_confirmation', label: '📧 Order Confirmation', desc: 'Confirm orders and build trust' }
  ];

  const localeOptions = [
    { value: 'it-IT', label: '🇮🇹 Italian', flag: '🇮🇹' },
    { value: 'en-US', label: '🇺🇸 English', flag: '🇺🇸' },
    { value: 'fr-FR', label: '🇫🇷 French', flag: '🇫🇷' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 hero-pattern">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-lg border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-black to-gray-800 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-lg">📧</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">EmailBuilder</h1>
                <p className="text-sm text-slate-600">AI-Powered Email Template Generator</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                ✅ All Services Running
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">

          {/* Configuration Panel */}
          <div className="xl:col-span-4 space-y-6">
            <div className="card p-6 animate-fadeIn">
              <div className="flex items-center space-x-3 mb-6">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-sm">⚙️</span>
                </div>
                <h2 className="text-xl font-bold text-slate-900">Configuration</h2>
              </div>

              <div className="space-y-6">
                {/* Template Type */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">
                    Template Type
                  </label>
                  <div className="space-y-2">
                    {templateOptions.map((option) => (
                      <div
                        key={option.value}
                        className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                          templateType === option.value
                            ? 'border-black bg-gray-50'
                            : 'border-slate-200 hover:border-slate-300 bg-white'
                        }`}
                        onClick={() => setTemplateType(option.value as TemplateType)}
                      >
                        <div className="font-medium text-slate-900">{option.label}</div>
                        <div className="text-sm text-slate-600">{option.desc}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Locale */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">
                    Language & Locale
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {localeOptions.map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setLocale(option.value)}
                        className={`p-3 rounded-lg border-2 text-center transition-all ${
                          locale === option.value
                            ? 'border-black bg-gray-50 text-black'
                            : 'border-slate-200 hover:border-slate-300 text-slate-700'
                        }`}
                      >
                        <div className="text-lg">{option.flag}</div>
                        <div className="text-xs font-medium">{option.label.split(' ')[1]}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* SKUs */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">
                    Product SKUs
                  </label>
                  <textarea
                    value={skus}
                    onChange={(e) => setSkus(e.target.value)}
                    placeholder="Enter product SKUs (comma-separated)&#10;Example: JACKET-001, BOOTS-002, BACKPACK-003"
                    className="input-field h-24 resize-none"
                  />
                  <p className="text-xs text-slate-500 mt-2">
                    💡 Add product SKUs to customize the email content
                  </p>
                </div>

                {/* Custom Template Upload */}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-3">
                    Custom Template (Optional)
                  </label>

                  {!uploadedTemplateId ? (
                    <div className="relative">
                      <input
                        ref={fileInputRef}
                        type="file"
                        onChange={handleFileUpload}
                        accept="image/*,.pdf,.doc,.docx"
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        disabled={isUploading}
                      />
                      <div className={`border-2 border-dashed border-slate-300 rounded-xl p-6 text-center transition-all ${
                        isUploading ? 'bg-slate-50' : 'hover:border-slate-400 hover:bg-slate-50'
                      }`}>
                        {isUploading ? (
                          <div className="flex items-center justify-center space-x-2">
                            <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                            <span className="text-slate-600">Uploading...</span>
                          </div>
                        ) : (
                          <>
                            <div className="w-12 h-12 bg-slate-200 rounded-lg flex items-center justify-center mx-auto mb-3">
                              <span className="text-xl">📎</span>
                            </div>
                            <p className="text-sm font-medium text-slate-900 mb-1">
                              Upload Template File
                            </p>
                            <p className="text-xs text-slate-500">
                              Images, PDFs, or documents with your template design
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-green-50 border-2 border-green-200 rounded-xl p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                            <span className="text-green-600 text-sm">✓</span>
                          </div>
                          <div>
                            <p className="text-sm font-medium text-green-900">
                              {uploadedFileName}
                            </p>
                            <p className="text-xs text-green-700">
                              Custom template uploaded
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={clearUploadedTemplate}
                          className="text-green-600 hover:text-green-800 p-1"
                        >
                          <span className="text-lg">✕</span>
                        </button>
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-slate-500 mt-2">
                    🎨 Upload a file containing your template graphics for personalized emails
                  </p>
                </div>

                {/* Generate Button */}
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating}
                  className={`btn-primary w-full text-lg font-semibold ${isGenerating ? 'animate-pulse-custom' : ''}`}
                >
                  {isGenerating ? (
                    <div className="flex items-center justify-center space-x-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Avviando Multi-Agent AI...</span>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center space-x-2">
                      <span>🤖</span>
                      <span>Generate Email with AI</span>
                    </div>
                  )}
                </button>

                {/* Error Display */}
                {generationError && (
                  <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 mt-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-red-100 rounded-lg flex items-center justify-center">
                        <span className="text-red-600 text-sm">⚠️</span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-red-900">
                          Errore nella generazione
                        </p>
                        <p className="text-xs text-red-700">
                          {generationError}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Stats */}
            <div className="card p-6 animate-fadeIn">
              <h3 className="font-bold text-slate-900 mb-4">✨ AI Features</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">🎯 Supervisor Agent - Orchestrazione</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">🔍 Retriever Agent - Dati prodotti</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">🎨 Asset Curator - Selezione immagini</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">✍️ Copywriter - Generazione testi</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">🏗️ Template Layout - Composizione</span>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-sm text-slate-600">⚡ Render Agent - Output finale</span>
                </div>
              </div>
            </div>
          </div>

          {/* Results Panel */}
          <div className="xl:col-span-8">
            <div className="card animate-fadeIn">
              {/* Tab Navigation */}
              <div className="border-b border-slate-200 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex space-x-1">
                    {[
                      { key: 'preview', label: '👁️ Preview', desc: 'Email preview' },
                      { key: 'json', label: '📋 JSON', desc: 'Template data' },
                      { key: 'mjml', label: '🔧 MJML', desc: 'Email markup' }
                    ].map((tab) => (
                      <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as 'preview' | 'json' | 'mjml')}
                        className={`px-4 py-2 rounded-lg font-medium transition-all ${
                          activeTab === tab.key
                            ? 'bg-black text-white'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                  {result && (
                    <div className="text-sm text-slate-500">
                      Generated: {new Date().toLocaleTimeString()}
                    </div>
                  )}
                </div>
              </div>

              {/* Tab Content */}
              <div className="p-6 min-h-[600px]">
                {!result ? (
                  <div className="flex flex-col items-center justify-center h-full text-center py-20">
                    <div className="w-20 h-20 bg-gradient-to-br from-slate-200 to-slate-300 rounded-2xl flex items-center justify-center mb-6">
                      <span className="text-3xl">📧</span>
                    </div>
                    <h3 className="text-xl font-bold text-slate-900 mb-2">Ready to Create</h3>
                    <p className="text-slate-600 max-w-md">
                      Configure your email template settings and click &quot;Generate Email&quot; to see your AI-powered email come to life.
                    </p>
                  </div>
                ) : (
                  <>
                    {activeTab === 'preview' && (
                      <div className="space-y-6">
                        {/* Email Headers */}
                        <div className="bg-slate-50 rounded-xl p-6 space-y-3">
                          <div className="flex items-start space-x-3">
                            <span className="text-sm font-semibold text-slate-700 w-20">Subject:</span>
                            <span className="text-slate-900 font-medium">{result.jsonTemplate.subject}</span>
                          </div>
                          <div className="flex items-start space-x-3">
                            <span className="text-sm font-semibold text-slate-700 w-20">Preview:</span>
                            <span className="text-slate-600">{result.jsonTemplate.preheader}</span>
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-sm font-semibold text-slate-700 w-20">Blocks:</span>
                            <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                              {result.jsonTemplate.blocks.length} sections
                            </span>
                          </div>
                        </div>

                        {/* Email Preview */}
                        <div className="border-2 border-slate-200 rounded-xl overflow-hidden">
                          <div className="bg-slate-100 px-4 py-2 text-sm text-slate-600 font-medium">
                            📱 Email Preview
                          </div>
                          <iframe
                            ref={iframeRef}
                            srcDoc={result.html}
                            className="w-full min-h-[600px]"
                            title="Email Preview"
                            style={{ border: 'none', height: '800px' }}
                            onLoad={resizeIframe}
                          />
                        </div>
                      </div>
                    )}

                    {activeTab === 'json' && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="font-semibold text-slate-900">Template JSON Structure</h3>
                          <button className="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium transition-colors">
                            📋 Copy JSON
                          </button>
                        </div>
                        <pre className="bg-slate-50 p-6 rounded-xl overflow-auto text-sm font-mono max-h-[500px] border">
                          {JSON.stringify(result.jsonTemplate, null, 2)}
                        </pre>
                      </div>
                    )}

                    {activeTab === 'mjml' && (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="font-semibold text-slate-900">MJML Email Markup</h3>
                          <button className="px-3 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm font-medium transition-colors">
                            📋 Copy MJML
                          </button>
                        </div>
                        <pre className="bg-slate-50 p-6 rounded-xl overflow-auto text-sm font-mono max-h-[500px] border">
                          {result.mjml}
                        </pre>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Multi-Agent Loader */}
      <MultiAgentLoader
        isVisible={showMultiAgentLoader}
        onComplete={handleGenerationComplete}
        onError={handleGenerationError}
        templateRequest={getCurrentTemplateRequest()}
      />
    </div>
  );
}
