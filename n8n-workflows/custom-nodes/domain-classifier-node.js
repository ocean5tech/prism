const { INodeType, INodeTypeDescription, INodeExecutionData } = require('n8n-workflow');

class DomainClassifierNode {
	description = {
		displayName: 'Domain Classifier',
		name: 'domainClassifier',
		group: ['transform'],
		version: 1,
		description: 'Classifies content into Finance, Sports, or Technology domains with confidence scoring',
		defaults: {
			name: 'Domain Classifier',
		},
		inputs: ['main'],
		outputs: ['main'],
		properties: [
			{
				displayName: 'Content Field',
				name: 'contentField',
				type: 'string',
				default: 'content',
				description: 'Field containing the content to classify',
				required: true,
			},
			{
				displayName: 'Title Field',
				name: 'titleField', 
				type: 'string',
				default: 'title',
				description: 'Field containing the title to help with classification',
			},
			{
				displayName: 'Confidence Threshold',
				name: 'confidenceThreshold',
				type: 'number',
				default: 0.7,
				description: 'Minimum confidence score required for domain assignment',
			},
			{
				displayName: 'API Endpoint',
				name: 'apiEndpoint',
				type: 'string',
				default: 'http://configuration-service:8000/api/v1/domains/classify',
				description: 'Classification service endpoint',
			},
			{
				displayName: 'API Token',
				name: 'apiToken',
				type: 'string',
				typeOptions: {
					password: true,
				},
				default: '={{$env.API_TOKEN}}',
				description: 'Authentication token for the classification service',
			}
		],
	};

	async execute() {
		const items = this.getInputData();
		const contentField = this.getNodeParameter('contentField', 0);
		const titleField = this.getNodeParameter('titleField', 0);  
		const confidenceThreshold = this.getNodeParameter('confidenceThreshold', 0);
		const apiEndpoint = this.getNodeParameter('apiEndpoint', 0);
		const apiToken = this.getNodeParameter('apiToken', 0);

		const returnData = [];

		for (let i = 0; i < items.length; i++) {
			const item = items[i];
			const content = item.json[contentField];
			const title = item.json[titleField] || '';

			try {
				// Call classification service
				const response = await this.helpers.request({
					method: 'POST',
					url: apiEndpoint,
					headers: {
						'Authorization': `Bearer ${apiToken}`,
						'Content-Type': 'application/json',
					},
					body: {
						content: content,
						title: title,
					},
					json: true,
				});

				// Process classification results
				const domainScores = response.domain_scores || {};
				const topDomain = Object.keys(domainScores).reduce((a, b) => 
					domainScores[a] > domainScores[b] ? a : b
				);
				const confidence = domainScores[topDomain] || 0;

				// Apply confidence threshold
				const finalDomain = confidence >= confidenceThreshold ? topDomain : 'unknown';

				// Add domain-specific style parameters
				const styleConfig = this.getDomainStyleConfig(finalDomain);

				returnData.push({
					json: {
						...item.json,
						domain: finalDomain,
						confidence_score: confidence,
						domain_scores: domainScores,
						style_config: styleConfig,
						classification_timestamp: new Date().toISOString(),
					},
				});

			} catch (error) {
				// Handle classification errors gracefully
				returnData.push({
					json: {
						...item.json,
						domain: 'unknown',
						confidence_score: 0,
						domain_scores: {},
						style_config: this.getDefaultStyleConfig(),
						classification_error: error.message,
						classification_timestamp: new Date().toISOString(),
					},
				});
			}
		}

		return [returnData];
	}

	getDomainStyleConfig(domain) {
		const styleConfigs = {
			finance: {
				tone: ['professional', 'analytical', 'authoritative'],
				structure: ['executive_summary', 'detailed_analysis', 'market_implications'],
				vocabulary: 'financial_technical',
				compliance_level: 'high',
				data_emphasis: true,
				risk_disclosure: true,
			},
			sports: {
				tone: ['dynamic', 'engaging', 'narrative'],
				structure: ['event_recap', 'player_analysis', 'predictions'],
				vocabulary: 'sports_accessible',
				real_time_focus: true,
				statistics_integration: true,
				fan_engagement: true,
			},
			technology: {
				tone: ['informative', 'forward_looking', 'technical'],
				structure: ['innovation_overview', 'technical_details', 'industry_impact'],
				vocabulary: 'tech_industry',
				trend_analysis: true,
				technical_depth: 'medium',
				future_implications: true,
			},
			unknown: this.getDefaultStyleConfig(),
		};

		return styleConfigs[domain] || this.getDefaultStyleConfig();
	}

	getDefaultStyleConfig() {
		return {
			tone: ['neutral', 'informative'],
			structure: ['introduction', 'main_content', 'conclusion'],
			vocabulary: 'general',
			safety_first: true,
		};
	}
}

module.exports = { nodeClass: DomainClassifierNode };