// 英文语言包
export default {
	// Common
	common: {
		appName: "MathModelAgent",
		loading: "Loading...",
		processing: "Processing...",
		confirm: "Confirm",
		cancel: "Cancel",
		save: "Save",
		delete: "Delete",
		edit: "Edit",
		close: "Close",
		back: "Back",
		more: "More",
		website: "Website",
		error: "Error",
		retry: "Retry",
		success: "Success",
		noData: "No data",
		copy: "Copy",
		copied: "Copied",
		reset: "Reset",
	},

	// Navigation
	nav: {
		features: "Features",
		workflow: "Workflow",
		agents: "Agents",
		login: "Sign In",
		getStartedFree: "Get Started",
		product: "Product",
		community: "Community",
		language: "Language",
		switchLang: "Switch Language",
	},

	// Home page
	home: {
		// Hero section
		heroTag: "AI-Powered Math Modeling Agent",
		heroTitle1: "Math Modeling Competition",
		heroTitle2: "From 3 Days to 1 Hour",
		heroDesc:
			"A multi-agent collaboration system that automates problem analysis, mathematical modeling, code implementation, and paper writing to produce award-winning papers.",
		ctaStart: "Get Started",
		ctaGithub: "View Source",

		// Stats
		statEfficiency: "Efficiency Boost",
		statAgents: "Collaborative Agents",
		statAutomation: "Automation",
		statEfficiencyValue: "72x",
		statAgentsValue: "5+",
		statAutomationValue: "End-to-End",

		// Workflow
		workflowTitle: "Four Steps to Complete Math Modeling",
		workflowDesc:
			"From uploading the problem to outputting the paper, fully automated",
		workflowStep1Title: "Upload Problem",
		workflowStep1Desc:
			"Upload competition problems and datasets. Supports .txt, .csv, .xlsx and other common formats.",
		workflowStep2Title: "Smart Analysis",
		workflowStep2Desc:
			"The modeling agent automatically analyzes the problem and selects the optimal mathematical model and solving strategy.",
		workflowStep3Title: "Code Implementation",
		workflowStep3Desc:
			"The coding agent writes Python code, executes it in a sandbox, and automatically debugs and optimizes.",
		workflowStep4Title: "Paper Output",
		workflowStep4Desc:
			"The writing agent generates a complete math modeling paper with charts, formulas, and references.",

		// Agents
		agentsTitle: "Multi-Agent Collaboration",
		agentsDesc:
			"Specialized division of labor, each performing their role, collaborating to produce high-quality results",
		agentCoordinator: "Coordinator",
		agentCoordinatorRole: "Coordinator Agent",
		agentCoordinatorDesc:
			"Analyzes task requirements, formulates solving plans, and orchestrates agent collaboration.",
		agentModeler: "Modeler",
		agentModelerRole: "Modeler Agent",
		agentModelerDesc:
			"Selects mathematical models, builds equation systems, and determines solving algorithms and parameters.",
		agentCoder: "Coder",
		agentCoderRole: "Coder Agent",
		agentCoderDesc:
			"Writes Python code, performs computations, generates visualizations, and auto-debugs.",
		agentWriter: "Writer",
		agentWriterRole: "Writer Agent",
		agentWriterDesc:
			"Writes complete papers with proper formatting, including abstract, body, charts, and references.",

		// Features
		featuresTitle: "Core Capabilities",
		featuresDesc:
			"Comprehensive capabilities tailored for math modeling competitions",
		feature1Title: "Smart Problem Analysis",
		feature1Desc:
			"Automatically parses competition problems, identifying key variables, constraints, and solving objectives.",
		feature2Title: "Data Visualization",
		feature2Desc:
			"Automatically generates statistical charts, heatmaps, scatter plots, and more to intuitively present analysis results.",
		feature3Title: "Code Sandbox Execution",
		feature3Desc:
			"Supports local Jupyter and cloud-based E2B for secure, isolated code execution environments.",
		feature4Title: "Multi-Model Support",
		feature4Desc:
			"Unified interface via LiteLLM, supporting DeepSeek, Claude, GPT, and other major models.",
		feature5Title: "Auto Paper Generation",
		feature5Desc:
			"Outputs fully structured Markdown papers with math formula and chart references.",
		feature6Title: "Smart Fault Tolerance",
		feature6Desc:
			"A2A auto-escalation mechanism that intelligently retries and switches to stronger models on code errors.",

		// CTA section
		ctaSectionTitle: "Ready to Get Started?",
		ctaSectionDesc:
			"Upload your problem and let AI handle the entire modeling, coding, and paper writing process for unprecedented efficiency.",
		ctaSectionButton: "Start for Free",
		ctaSectionNote: "No credit card required, start immediately",

		// Footer
		footerDesc:
			"AI-powered math modeling agent that automates the entire process from analysis to paper through multi-agent collaboration.",
		footerCopyright: "\u00A9 {year} MathModelAgent. All rights reserved.",
		footerSlogan: "Built with AI, for Mathematicians.",
	},

	// Login page
	login: {
		welcomeBack: "Welcome",
		loginDesc: "Sign in with your Google account to use MathModelAgent",
		googleButton: "Sign in with Google",
		googleHint: "We'll use your Google account for secure authentication",
		termsText: "By continuing, you agree to our",
		termsOfService: "Terms of Service",
		and: "and",
		privacyPolicy: "Privacy Policy",
		// Google OAuth error messages
		errorTokenExchange: "Authentication failed, please try again",
		errorUserInfo: "Failed to get user info, please try again",
		errorAccountDisabled: "This account has been disabled",
		errorServer: "Server error, please try again later",
		errorMissingCode: "Missing authentication info, please try again",
		errorUnknown: "Login failed, please try again",
		// Login page right panel
		slogan: "AI-Powered Math Modeling Assistant",
		featureMultiAgent: "Multi-Agent Collaboration",
		featureMultiAgentDesc: "Agents working together to solve problems",
		featureCodeSandbox: "Code Execution Sandbox",
		featureCodeSandboxDesc: "Secure isolated runtime environment",
		featurePaperGen: "Auto Paper Generation",
		featurePaperGenDesc: "One-click complete paper output",
	},

	// Chat page
	chat: {
		more: "More",
		website: "Website",
		newTask: "Start New Task",
		historyTasks: "Task History",
		noHistory: "No tasks yet",
		start: "Start",
	},

	// Chat home
	chatHome: {
		welcomeTitle: "How can I help you?",
		welcomeDesc:
			"Upload problems and data, AI agents will automatically complete modeling, coding, and paper writing",
		agentCoordinator: "Task Scheduling",
		agentModeler: "Math Modeling",
		agentCoder: "Code Execution",
		agentWriter: "Paper Writing",
		examplesTitle: "Quick Start: Select a sample problem",
		dropFiles: "Release to upload files",
		dropFilesHint: "Supports .txt, .csv, .xlsx and more",
		textareaPlaceholder:
			"Paste the complete math modeling problem... (Ctrl+Enter to submit)",
		uploadTooltip: "Upload data files",
		settingsTooltip: "Task parameter settings",
		submitting: "Submitting...",
		startAnalysis: "Start Analysis",
		bottomHint:
			"After submission, AI agents will work collaboratively with no intervention needed",
		fileAdded: "Files added",
		fileAddedDesc: "{count} file(s) added",
		confirmContinue: "Confirm to continue",
		noFileWarning:
			"You have not uploaded any data files. Some problems require datasets for analysis. Continue anyway?",
		goUpload: "Upload files",
		continueSubmit: "Continue",
		configureApiKey: "Please configure API Key first",
		configureApiKeyDesc:
			"Go to Sidebar bottom -> Avatar -> API Key to configure",
		taskSubmitted: "Task submitted successfully",
		taskId: "Task ID: {id}",
		taskSubmitFailed: "Task submission failed",
		taskSubmitFailedDesc:
			"Please check network connection and API Key configuration",
		loadExampleFailed: "Failed to load example",
		loadExampleFailedDesc: "Please try again later",
		// Parameter options
		templateLabel: "Template",
		templatePlaceholder: "Select template",
		templateNational: "CUMCM",
		templateMCM: "MCM/ICM",
		languageLabel: "Language",
		languagePlaceholder: "Select language",
		languageChinese: "Chinese",
		languageEnglish: "English",
		formatLabel: "Format",
		formatPlaceholder: "Select format",
		formatLatexHint: "Recommended for MCM, uses mcmthesis template",
		workflowLabel: "Workflow Mode",
		workflowPlaceholder: "Select workflow",
		workflowSmart: "Smart Mode",
		workflowSmartHint: "Auto-select based on problem complexity",
		workflowStandard: "Standard Mode",
		workflowStandardHint: "Fast pipeline, for simple problems",
		workflowEnhanced: "Enhanced Mode",
		workflowEnhancedHint: "With feedback loops and quality review (Token +50%)",
		workflowAward: "Award-Winning Mode",
		workflowAwardHint:
			"Full collaboration with research+abstract+LaTeX (Token +80%)",
		// Example data
		example1Title: "Impact of Maternal Health on Infant Growth",
		example1Source: "2023 HuaShu Cup Problem C",
		example1Tag1: "Classification",
		example1Tag2: "Health",
		example2Title: "Social Media Platform User Analysis",
		example2Source: "2025 May Day Cup Problem C",
		example2Tag1: "Social Media",
		example2Tag2: "User Behavior",
		example3Title: "Crop Planting Strategy",
		example3Source: "2024 CUMCM Problem C",
		example3Tag1: "Planting Strategy",
		example3Tag2: "Optimization",
	},

	// API settings dialog
	apiDialog: {
		title: "Settings",
		description:
			"Manage API provider configuration, assign models for each Agent",
		scholarSearch: "Academic Literature Search",
		optional: "Optional",
		scholarDesc:
			"After configuring email, the writer agent will automatically search for academic references and get higher API rate limits",
		openalexLabel: "OpenAlex Email",
		validating: "Validating...",
		validate: "Validate",
		openalexHint:
			"Providing an email joins the OpenAlex Polite Pool for faster request rates. Leave empty to skip literature search.",
		saving: "Saving...",
		saveConfig: "Save Configuration",
		emailFormatError: "Invalid email format",
		emailFormatErrorDesc: "Please enter a valid email address",
		verifySuccess: "Verification successful",
		verifyFailed: "Verification failed",
		verifyServiceFailed: "Unable to connect to OpenAlex service",
		connectionSuccess: "Connection successful",
		connectionFailed: "Connection failed",
		testFailed: "Test failed",
		testServiceFailed: "Unable to connect to validation service",
		saveSuccess: "Saved successfully",
		saveSuccessDesc: "Configuration saved",
		saveFailed: "Save failed",
		saveFailedDesc: "Unable to save configuration",
	},

	// Settings panel
	settings: {
		deleteProviderWarning: "This provider is used by the following Agents. Deleting it will unlink them: ",
	},

	// Provider configuration
	provider: {
		config: "Provider Configuration",
		addProvider: "Add Provider",
		noProviders: "No providers configured",
		addFirst: "Add your first provider",
		headerName: "Provider",
		headerApiKey: "API Key",
		headerBaseUrl: "Base URL",
		headerStatus: "Status",
		headerActions: "Actions",
		statusValid: "Valid",
		statusInvalid: "Invalid",
		statusUntested: "Untested",
		editTooltip: "Edit",
		testTooltip: "Test connection",
		deleteTooltip: "Delete",
	},

	// Agent assignment
	agent: {
		assignTitle: "Agent Model Assignment",
		assignDesc: "Assign AI providers for each Agent",
		coordinator: "Coordinator",
		coordinatorDesc: "Task decomposition and coordination",
		modeler: "Modeler",
		modelerDesc: "Mathematical modeling",
		coder: "Coder",
		coderDesc: "Code implementation",
		writer: "Writer",
		writerDesc: "Paper writing",
		addProviderFirst: "Please add a provider first",
		selectProvider: "Select provider...",
	},

	// Provider edit dialog
	providerEdit: {
		addTitle: "Add Provider",
		editTitle: "Edit Provider",
		dialogDesc: "Configure API provider connection details",
		presetTemplate: "Preset Template",
		templatePlaceholder: "Select a preset template to auto-fill...",
		commonProviders: "Common Providers",
		providerName: "Provider Name",
		providerNamePlaceholder: "e.g., My DeepSeek",
		apiKeyLabel: "API Key",
		apiKeyPlaceholder: "Enter API Key",
		baseUrlLabel: "Base URL",
		modelIdLabel: "Model ID",
		modelIdPlaceholder: "Model name, e.g., gpt-4o",
		apiProtocol: "API Protocol",
		endpoint: "Endpoint",
		testing: "Testing...",
		testConnection: "Test Connection",
		connectionFailed:
			"Connection failed: Unable to connect to validation service",
		custom: "Custom",
		openaiProtocol: "OpenAI Protocol",
		anthropicProtocol: "Anthropic Protocol",
		geminiProtocol: "Gemini Protocol",
	},

	// About dialog
	about: {
		title: "About MathModelAgent",
		version: "AI Math Modeling Agent v0.1.0",
		coreFeatures: "Core Features",
		multiAgent:
			"Multi-Agent Collaboration (Coordinator / Modeler / Coder / Writer)",
		codeExec: "Code Execution & Debugging (Jupyter / E2B)",
		paperGen: "Auto Paper Generation (Markdown)",
		outputDir: "Output Directory",
		notebookDesc: "Code execution process",
		paperDesc: "Generated paper (Markdown)",
		customConfig: "Custom Configuration",
		template: "Template",
		prompts: "Prompts",
		helpSupport: "Help & Support",
		docs: "Documentation",
		qqGroup: "QQ Group",
	},

	// User menu
	user: {
		guest: "Guest",
		clickToLogin: "Click to sign in",
		credits: "Credits",
		apiKey: "API Key",
		accountSettings: "Account Settings",
		logout: "Sign Out",
		loginOrRegister: "Sign In",
	},

	// Error messages
	errors: {
		networkError:
			"Network connection failed, please check your network settings",
		serverError: "Server error, please try again later",
		unauthorized: "Unauthorized, please sign in again",
		notFound: "Page not found",
		timeout: "Request timed out, please retry",
		unknown: "An unknown error occurred",
	},
};
