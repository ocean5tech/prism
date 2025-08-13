/**
 * Content Intelligence Custom Node
 * Advanced content analysis, optimization, and intelligence extraction
 */

class ContentIntelligenceNode {
  constructor() {
    this.description = {
      displayName: 'Content Intelligence',
      name: 'contentIntelligence',
      group: ['prism'],
      version: 1,
      description: 'Advanced content analysis and intelligence extraction for multi-domain content optimization',
      defaults: {
        name: 'Content Intelligence'
      },
      inputs: ['main'],
      outputs: ['main'],
      properties: [
        {
          displayName: 'Operation',
          name: 'operation',
          type: 'options',
          options: [
            {
              name: 'Analyze Content Quality',
              value: 'analyzeQuality'
            },
            {
              name: 'Extract Content Insights',
              value: 'extractInsights'
            },
            {
              name: 'Optimize for Domain',
              value: 'optimizeForDomain'
            },
            {
              name: 'Generate Content Variations',
              value: 'generateVariations'
            },
            {
              name: 'Detect Content Patterns',
              value: 'detectPatterns'
            }
          ],
          default: 'analyzeQuality'
        },
        {
          displayName: 'Domain',
          name: 'domain',
          type: 'options',
          options: [
            { name: 'Finance', value: 'finance' },
            { name: 'Sports', value: 'sports' },
            { name: 'Technology', value: 'technology' },
            { name: 'General', value: 'general' }
          ],
          default: 'general'
        },
        {
          displayName: 'Content Field',
          name: 'contentField',
          type: 'string',
          default: 'content',
          description: 'Name of the field containing the content to analyze'
        },
        {
          displayName: 'Analysis Depth',
          name: 'analysisDepth',
          type: 'options',
          options: [
            { name: 'Basic', value: 'basic' },
            { name: 'Standard', value: 'standard' },
            { name: 'Deep', value: 'deep' }
          ],
          default: 'standard'
        }
      ]
    };
  }

  async execute(context) {
    const items = context.getInputData();
    const returnData = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      const operation = context.getNodeParameter('operation', i);
      const domain = context.getNodeParameter('domain', i);
      const contentField = context.getNodeParameter('contentField', i);
      const analysisDepth = context.getNodeParameter('analysisDepth', i);

      const content = item.json[contentField];
      if (!content) {
        throw new Error(`Content field '${contentField}' not found in input data`);
      }

      let result;

      switch (operation) {
        case 'analyzeQuality':
          result = await this.analyzeContentQuality(content, domain, analysisDepth);
          break;
        case 'extractInsights':
          result = await this.extractContentInsights(content, domain, analysisDepth);
          break;
        case 'optimizeForDomain':
          result = await this.optimizeContentForDomain(content, domain, analysisDepth);
          break;
        case 'generateVariations':
          result = await this.generateContentVariations(content, domain);
          break;
        case 'detectPatterns':
          result = await this.detectContentPatterns(content, domain);
          break;
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }

      returnData.push({
        json: {
          ...item.json,
          contentIntelligence: result,
          operation: operation,
          analysisTimestamp: new Date().toISOString()
        }
      });
    }

    return [returnData];
  }

  async analyzeContentQuality(content, domain, depth) {
    const analysis = {
      overallScore: 0,
      dimensions: {},
      recommendations: [],
      issues: []
    };

    // Readability Analysis
    const readability = this.analyzeReadability(content);
    analysis.dimensions.readability = readability;

    // Domain-specific Quality Analysis
    const domainQuality = this.analyzeDomainQuality(content, domain);
    analysis.dimensions.domainRelevance = domainQuality;

    // Structure Analysis
    const structure = this.analyzeStructure(content);
    analysis.dimensions.structure = structure;

    // Engagement Analysis
    const engagement = this.analyzeEngagement(content, domain);
    analysis.dimensions.engagement = engagement;

    // Uniqueness Analysis (AI pattern detection)
    const uniqueness = this.analyzeUniqueness(content);
    analysis.dimensions.uniqueness = uniqueness;

    if (depth === 'deep') {
      // Advanced semantic analysis
      const semantics = this.analyzeSemantics(content, domain);
      analysis.dimensions.semantics = semantics;

      // Fact-checking analysis
      const factuality = this.analyzeFactuality(content, domain);
      analysis.dimensions.factuality = factuality;
    }

    // Calculate overall score
    const weights = {
      readability: 0.2,
      domainRelevance: 0.25,
      structure: 0.15,
      engagement: 0.25,
      uniqueness: 0.15
    };

    if (depth === 'deep') {
      weights.semantics = 0.1;
      weights.factuality = 0.1;
      // Adjust other weights proportionally
      Object.keys(weights).forEach(key => {
        if (!['semantics', 'factuality'].includes(key)) {
          weights[key] *= 0.8;
        }
      });
    }

    analysis.overallScore = Object.entries(weights).reduce((sum, [dimension, weight]) => {
      const score = analysis.dimensions[dimension]?.score || 0;
      return sum + (score * weight);
    }, 0);

    // Generate recommendations
    analysis.recommendations = this.generateQualityRecommendations(analysis.dimensions);

    return analysis;
  }

  analyzeReadability(content) {
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const words = content.split(/\\s+/).filter(w => w.length > 0);
    const syllables = words.reduce((sum, word) => {
      return sum + this.countSyllables(word);
    }, 0);

    const avgWordsPerSentence = words.length / sentences.length;
    const avgSyllablesPerWord = syllables / words.length;

    // Flesch-Kincaid Grade Level
    const gradeLevel = 0.39 * avgWordsPerSentence + 11.8 * avgSyllablesPerWord - 15.59;
    
    // Flesch Reading Ease
    const readingEase = 206.835 - (1.015 * avgWordsPerSentence) - (84.6 * avgSyllablesPerWord);

    return {
      score: Math.max(0, Math.min(100, readingEase)),
      gradeLevel: Math.max(0, gradeLevel),
      avgWordsPerSentence,
      avgSyllablesPerWord,
      totalWords: words.length,
      totalSentences: sentences.length,
      classification: this.classifyReadability(readingEase)
    };
  }

  analyzeDomainQuality(content, domain) {
    const domainTerms = {
      finance: [
        'market', 'investment', 'stock', 'portfolio', 'dividend', 'earnings',
        'revenue', 'profit', 'loss', 'capital', 'asset', 'liability',
        'equity', 'debt', 'bond', 'commodity', 'currency', 'inflation'
      ],
      sports: [
        'team', 'player', 'game', 'match', 'season', 'championship',
        'league', 'score', 'victory', 'tournament', 'coach', 'athlete',
        'performance', 'statistics', 'record', 'playoff', 'draft', 'training'
      ],
      technology: [
        'software', 'hardware', 'application', 'system', 'platform',
        'digital', 'innovation', 'development', 'programming', 'algorithm',
        'data', 'artificial intelligence', 'machine learning', 'cloud',
        'cybersecurity', 'blockchain', 'API', 'database'
      ]
    };

    const terms = domainTerms[domain] || [];
    const contentLower = content.toLowerCase();
    
    const foundTerms = terms.filter(term => contentLower.includes(term.toLowerCase()));
    const coverage = terms.length > 0 ? (foundTerms.length / terms.length) * 100 : 50;

    // Analyze term frequency and context
    const termFrequency = foundTerms.reduce((freq, term) => {
      const matches = (contentLower.match(new RegExp(term.toLowerCase(), 'g')) || []).length;
      freq[term] = matches;
      return freq;
    }, {});

    return {
      score: Math.min(100, coverage + 20), // Base score plus bonus
      coverage,
      foundTerms,
      termFrequency,
      domainExpertise: this.assessDomainExpertise(content, domain)
    };
  }

  analyzeStructure(content) {
    const paragraphs = content.split(/\\n\\s*\\n/).filter(p => p.trim().length > 0);
    const headers = (content.match(/^#{1,6}\\s+.+$/gm) || []).length;
    const lists = (content.match(/^\\s*[•-]|^\\s*\\d+\\./gm) || []).length;
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);

    // Analyze paragraph structure
    const avgParagraphLength = paragraphs.reduce((sum, p) => {
      return sum + p.split(/[.!?]+/).length;
    }, 0) / paragraphs.length;

    // Analyze logical flow
    const transitionWords = [
      'however', 'therefore', 'moreover', 'furthermore', 'additionally',
      'consequently', 'meanwhile', 'similarly', 'in contrast', 'for example'
    ];

    const transitionCount = transitionWords.reduce((count, word) => {
      return count + (content.toLowerCase().match(new RegExp(`\\\\b${word}\\\\b`, 'g')) || []).length;
    }, 0);

    let structureScore = 0;

    // Scoring based on structural elements
    if (avgParagraphLength >= 3 && avgParagraphLength <= 6) structureScore += 25;
    if (headers > 0) structureScore += 20;
    if (lists > 0) structureScore += 15;
    if (transitionCount >= 2) structureScore += 20;
    if (paragraphs.length >= 3) structureScore += 20;

    return {
      score: Math.min(100, structureScore),
      paragraphs: paragraphs.length,
      headers,
      lists,
      avgParagraphLength,
      transitionWords: transitionCount,
      logicalFlow: transitionCount / paragraphs.length
    };
  }

  analyzeEngagement(content, domain) {
    const engagementWords = {
      finance: ['opportunity', 'growth', 'potential', 'strategy', 'advantage', 'profit', 'success'],
      sports: ['exciting', 'thrilling', 'amazing', 'incredible', 'victory', 'champion', 'record'],
      technology: ['innovative', 'breakthrough', 'revolutionary', 'advanced', 'cutting-edge', 'future'],
      general: ['important', 'significant', 'valuable', 'effective', 'successful', 'essential']
    };

    const words = engagementWords[domain] || engagementWords.general;
    const contentLower = content.toLowerCase();

    let engagementScore = 0;

    // Count engagement words
    words.forEach(word => {
      const matches = (contentLower.match(new RegExp(`\\\\b${word}\\\\b`, 'g')) || []).length;
      engagementScore += matches * 3;
    });

    // Analyze questions and calls to action
    const questions = (content.match(/\\?/g) || []).length;
    const callsToAction = (contentLower.match(/\\b(discover|learn|find|explore|consider|try)\\b/g) || []).length;
    const emotionalWords = (contentLower.match(/\\b(amazing|incredible|outstanding|excellent|remarkable|extraordinary)\\b/g) || []).length;

    engagementScore += questions * 4 + callsToAction * 3 + emotionalWords * 2;

    return {
      score: Math.min(100, engagementScore),
      questions,
      callsToAction,
      emotionalWords,
      engagementWords: words.filter(word => contentLower.includes(word)).length
    };
  }

  analyzeUniqueness(content) {
    // Detect common AI patterns
    const aiPatterns = [
      /\\bin conclusion\\b/gi,
      /\\bit's important to note\\b/gi,
      /\\bit's worth noting\\b/gi,
      /\\bin summary\\b/gi,
      /\\boverall\\b.*\\bit can be said\\b/gi,
      /\\bthe key takeaway\\b/gi,
      /\\bto summarize\\b/gi,
      /\\bas we can see\\b/gi
    ];

    let patternCount = 0;
    const foundPatterns = [];

    aiPatterns.forEach(pattern => {
      const matches = content.match(pattern);
      if (matches) {
        patternCount += matches.length;
        foundPatterns.push(...matches);
      }
    });

    // Analyze sentence structure repetition
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const sentenceStarts = sentences.map(s => s.trim().split(' ').slice(0, 3).join(' ').toLowerCase());
    const uniqueStarts = new Set(sentenceStarts);
    const repetitionRatio = 1 - (uniqueStarts.size / sentenceStarts.length);

    const uniquenessScore = Math.max(0, 100 - (patternCount * 15 + repetitionRatio * 30));

    return {
      score: uniquenessScore,
      aiPatternCount: patternCount,
      foundPatterns,
      repetitionRatio,
      uniqueSentenceStarts: uniqueStarts.size,
      totalSentences: sentences.length
    };
  }

  analyzeSemantics(content, domain) {
    // Advanced semantic analysis would typically use NLP libraries
    // This is a simplified version focusing on semantic coherence

    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const words = content.toLowerCase().split(/\\s+/);
    const wordFreq = {};

    words.forEach(word => {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    });

    // Calculate lexical diversity
    const uniqueWords = Object.keys(wordFreq).length;
    const lexicalDiversity = uniqueWords / words.length;

    // Analyze topic coherence (simplified)
    const topicWords = Object.entries(wordFreq)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([word]) => word);

    return {
      score: Math.min(100, lexicalDiversity * 100 + 20),
      lexicalDiversity,
      uniqueWords,
      totalWords: words.length,
      topicWords,
      coherenceIndicators: this.analyzeCoherence(sentences)
    };
  }

  analyzeFactuality(content, domain) {
    // Simplified factuality analysis
    // In production, this would use fact-checking APIs

    const factualIndicators = [
      /\\d{4}/, // Years
      /\\d+%/, // Percentages  
      /\\$\\d+/, // Dollar amounts
      /according to/gi,
      /research shows/gi,
      /study found/gi,
      /data indicates/gi
    ];

    let factualityScore = 50; // Base score

    factualIndicators.forEach(pattern => {
      const matches = content.match(pattern);
      if (matches) {
        factualityScore += matches.length * 5;
      }
    });

    // Check for hedging language (reduces certainty but increases accuracy)
    const hedgingWords = ['may', 'might', 'could', 'possibly', 'likely', 'appears'];
    const hedging = hedgingWords.reduce((count, word) => {
      return count + (content.toLowerCase().match(new RegExp(`\\\\b${word}\\\\b`, 'g')) || []).length;
    }, 0);

    return {
      score: Math.min(100, factualityScore),
      factualIndicators: factualIndicators.reduce((count, pattern) => {
        return count + (content.match(pattern) || []).length;
      }, 0),
      hedgingLanguage: hedging,
      confidenceLevel: hedging > 0 ? 'measured' : 'confident'
    };
  }

  generateQualityRecommendations(dimensions) {
    const recommendations = [];

    if (dimensions.readability?.score < 60) {
      recommendations.push({
        type: 'readability',
        priority: 'high',
        message: 'Improve readability by using shorter sentences and simpler vocabulary',
        impact: 'medium'
      });
    }

    if (dimensions.domainRelevance?.score < 70) {
      recommendations.push({
        type: 'domain_relevance',
        priority: 'high',
        message: 'Include more domain-specific terminology and concepts',
        impact: 'high'
      });
    }

    if (dimensions.structure?.score < 60) {
      recommendations.push({
        type: 'structure',
        priority: 'medium',
        message: 'Add headers, improve paragraph structure, and use transition words',
        impact: 'medium'
      });
    }

    if (dimensions.engagement?.score < 50) {
      recommendations.push({
        type: 'engagement',
        priority: 'high',
        message: 'Add more engaging language, questions, and calls to action',
        impact: 'high'
      });
    }

    if (dimensions.uniqueness?.score < 70) {
      recommendations.push({
        type: 'uniqueness',
        priority: 'high',
        message: 'Remove AI-like patterns and vary sentence structures',
        impact: 'high'
      });
    }

    return recommendations;
  }

  // Helper methods
  countSyllables(word) {
    return word.toLowerCase().match(/[aeiouy]+/g)?.length || 1;
  }

  classifyReadability(score) {
    if (score >= 90) return 'very_easy';
    if (score >= 80) return 'easy';
    if (score >= 70) return 'fairly_easy';
    if (score >= 60) return 'standard';
    if (score >= 50) return 'fairly_difficult';
    if (score >= 30) return 'difficult';
    return 'very_difficult';
  }

  assessDomainExpertise(content, domain) {
    // Simplified domain expertise assessment
    const expertiseIndicators = {
      finance: ['portfolio optimization', 'risk assessment', 'market volatility', 'regulatory compliance'],
      sports: ['statistical analysis', 'performance metrics', 'strategic coaching', 'athletic development'],
      technology: ['system architecture', 'scalability', 'optimization algorithms', 'technical implementation']
    };

    const indicators = expertiseIndicators[domain] || [];
    const contentLower = content.toLowerCase();
    const foundIndicators = indicators.filter(indicator => 
      contentLower.includes(indicator.toLowerCase())
    );

    return {
      level: foundIndicators.length > 2 ? 'expert' : foundIndicators.length > 0 ? 'intermediate' : 'basic',
      indicators: foundIndicators.length,
      total: indicators.length
    };
  }

  analyzeCoherence(sentences) {
    // Simplified coherence analysis
    const pronouns = ['it', 'this', 'that', 'these', 'those', 'they', 'them'];
    let coherenceScore = 0;

    sentences.forEach((sentence, index) => {
      if (index > 0) {
        const words = sentence.toLowerCase().split(/\\s+/);
        const hasPronouns = pronouns.some(pronoun => words.includes(pronoun));
        if (hasPronouns) coherenceScore++;
      }
    });

    return {
      score: sentences.length > 1 ? (coherenceScore / (sentences.length - 1)) * 100 : 100,
      coherentSentences: coherenceScore,
      totalSentences: sentences.length
    };
  }

  async extractContentInsights(content, domain, depth) {
    // Implementation for content insights extraction
    return {
      keyTopics: this.extractKeyTopics(content, domain),
      sentiment: this.analyzeSentiment(content),
      complexity: this.analyzeComplexity(content),
      targetAudience: this.identifyTargetAudience(content, domain),
      contentType: this.classifyContentType(content),
      keyPhrases: this.extractKeyPhrases(content)
    };
  }

  async optimizeContentForDomain(content, domain, depth) {
    // Implementation for domain-specific optimization
    return {
      originalContent: content,
      optimizationSuggestions: this.generateOptimizationSuggestions(content, domain),
      domainAlignment: this.analyzeDomainAlignment(content, domain),
      targetModifications: this.suggestTargetModifications(content, domain)
    };
  }

  async generateContentVariations(content, domain) {
    // Implementation for content variation generation
    return {
      variations: this.createContentVariations(content, domain),
      styleAlternatives: this.generateStyleAlternatives(content),
      lengthVariations: this.createLengthVariations(content)
    };
  }

  async detectContentPatterns(content, domain) {
    // Implementation for pattern detection
    return {
      structuralPatterns: this.identifyStructuralPatterns(content),
      linguisticPatterns: this.identifyLinguisticPatterns(content),
      domainPatterns: this.identifyDomainPatterns(content, domain),
      repetitiveElements: this.findRepetitiveElements(content)
    };
  }

  // Additional helper methods for the extended functionality would go here...
}

module.exports = ContentIntelligenceNode;