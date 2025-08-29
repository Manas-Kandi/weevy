'''<script lang="ts">
	import { createEventDispatcher, tick, onMount } from 'svelte';
	import type { Node } from './types';
	import { Brain, FileInput, FileOutput, BookOpen, Wrench, Sparkles, Zap, Database } from 'lucide-svelte';
	import { scale, fly } from 'svelte/transition';
	import { elasticOut, cubicInOut } from 'svelte/easing';

	export let node: Node;
	export let selected: boolean = false;

	let focused = false;
	let hovering = false;
	// Connection-related state
	let showInputPort = false;
	let showOutputPort = false;
	let isDraggingConnection = false;
	let connectionStartPoint: { x: number; y: number } | null = null;
	let connectionCurrentPoint: { x: number; y: number } | null = null;
	let titleEl: HTMLTextAreaElement;
	let descEl: HTMLTextAreaElement;
	
	// External App specific state
	let showAppAutocomplete = false;
	let appSearchQuery = '';
	let selectedAppIndex = -1;

	// Input Node specific state
	let inputType = 'text'; // text, file, button, form, multiple-choice
	let inputValue = '';
	let testData = '';
	let showTypeSelector = false;
	let files: FileList | null = null;
	let multipleChoiceOptions = ['Option 1', 'Option 2', 'Option 3'];
	let selectedChoice = '';
	let formFields = [
		{ label: 'Name', value: '', type: 'text' },
		{ label: 'Email', value: '', type: 'email' }
	];

	const dispatch = createEventDispatcher<{
		select: void;
		connectionStart: { nodeId: string; port: 'output'; startPoint: { x: number; y: number } };
		connectionTarget: { nodeId: string; port: 'input' };
		connectionDrag: { nodeId: string; startPoint: { x: number; y: number }; currentPoint: { x: number; y: number } };
		connectionComplete: { fromNodeId: string; toNodeId: string; fromPort: string; toPort: string };
		connectionCancel: { nodeId: string };
		nodestartdrag: { nodeId: string; event: MouseEvent };
		delete: { nodeId: string };
	}>();

	const nodeIcons = {
		brain: Brain,
		input: FileInput,
		output: FileOutput,
		knowledge: BookOpen,
		tool: Wrench,
		externalApp: Database
	};

	const nodeAnimationIcons = {
		brain: Zap,
		input: Sparkles,
		output: Sparkles,
		knowledge: Database,
		tool: Wrench,
		externalApp: Sparkles
	};

	const nodeColors: Record<string, string> = {
		brain: '#8B5CF6',
		input: '#3B82F6', 
		output: '#10B981',
		knowledge: '#6366F1',
		tool: '#F59E0B',
		externalApp: '#EC4899'
	};

	
	// Available apps for autocomplete - Comprehensive Library
	const availableApps = [
		// Communication
		{ id: 'gmail', name: 'Gmail', description: 'Email service', icon: '📧', category: 'communication' },
		{ id: 'slack', name: 'Slack', description: 'Team communication', icon: '💬', category: 'communication' },
		{ id: 'teams', name: 'Microsoft Teams', description: 'Team collaboration', icon: '👥', category: 'communication' },
		{ id: 'discord', name: 'Discord', description: 'Gaming community', icon: '🎮', category: 'communication' },
		{ id: 'whatsapp', name: 'WhatsApp Business', description: 'Business messaging', icon: '💬', category: 'communication' },
		
		// Project Management
		{ id: 'jira', name: 'JIRA', description: 'Issue tracking', icon: '🎫', category: 'project' },
		{ id: 'linear', name: 'Linear', description: 'Software development', icon: '📈', category: 'project' },
		{ id: 'asana', name: 'Asana', description: 'Task management', icon: '✅', category: 'project' },
		{ id: 'monday', name: 'Monday.com', description: 'Work management', icon: '📊', category: 'project' },
		{ id: 'trello', name: 'Trello', description: 'Kanban boards', icon: '📋', category: 'project' },
		
		// CRM & Sales
		{ id: 'salesforce', name: 'Salesforce', description: 'CRM platform', icon: '☁️', category: 'crm' },
		{ id: 'hubspot', name: 'HubSpot', description: 'Marketing & sales', icon: '🎯', category: 'crm' },
		{ id: 'pipedrive', name: 'Pipedrive', description: 'Sales CRM', icon: '💼', category: 'crm' },
		
		// Data & Analytics
		{ id: 'analytics', name: 'Google Analytics', description: 'Web analytics', icon: '📈', category: 'data' },
		{ id: 'mixpanel', name: 'Mixpanel', description: 'Product analytics', icon: '📊', category: 'data' },
		{ id: 'sheets', name: 'Google Sheets', description: 'Spreadsheet tool', icon: '📊', category: 'data' },
		{ id: 'airtable', name: 'Airtable', description: 'Database tool', icon: '🗃️', category: 'data' },
		
		// Marketing
		{ id: 'mailchimp', name: 'Mailchimp', description: 'Email marketing', icon: '📧', category: 'marketing' },
		{ id: 'intercom', name: 'Intercom', description: 'Customer messaging', icon: '💬', category: 'marketing' },
		{ id: 'zapier', name: 'Zapier', description: 'Automation tool', icon: '🔗', category: 'marketing' },
		
		// Development
		{ id: 'github', name: 'GitHub', description: 'Code collaboration', icon: '💻', category: 'development' },
		{ id: 'gitlab', name: 'GitLab', description: 'DevOps platform', icon: '🚀', category: 'development' },
		
		// Documentation
		{ id: 'notion', name: 'Notion', description: 'Workspace platform', icon: '📝', category: 'documentation' },
		{ id: 'confluence', name: 'Confluence', description: 'Team collaboration', icon: '📖', category: 'documentation' }
	];

	// Configuration for each app's dynamic fields
	const appFieldConfigs: Record<string, { key: string; label: string; placeholder: string }[]> = {
		gmail: [
			{ key: 'email', label: 'Email Address', placeholder: 'Enter email address' },
			{ key: 'subject', label: 'Subject', placeholder: 'Enter email subject' }
		],
		slack: [
			{ key: 'channel', label: 'Channel', placeholder: '#general' },
			{ key: 'message', label: 'Message', placeholder: 'Enter your message' }
		],
		jira: [
			{ key: 'project', label: 'Project Key', placeholder: 'PROJ' },
			{ key: 'issueType', label: 'Issue Type', placeholder: 'Task' }
		],
		github: [
			{ key: 'repository', label: 'Repository', placeholder: 'owner/repo' },
			{ key: 'issueNumber', label: 'Issue Number', placeholder: '123' }
		],
		// Add other app configs here
	};

	// Filtered apps for autocomplete (simplified)
	$: filteredApps = appSearchQuery.length === 0 
		? availableApps 
		: availableApps.filter(app => 
			app.name.toLowerCase().includes(appSearchQuery.toLowerCase()) ||
			app.description.toLowerCase().includes(appSearchQuery.toLowerCase())
		);

	
	const nodeTypeLabels: Record<string, string> = {
		brain: 'AI Brain Node',
		input: 'Input Node',
		output: 'Output Node',
		knowledge: 'Knowledge Node',
		tool: 'Tool Node',
		externalApp: 'External App Node'
	};

	const defaultTitles: Record<string, string> = {
		brain: 'Descriptive title of the thinking',
		input: 'Descriptive title of the input',
		output: 'Descriptive title of the output',
		knowledge: 'Descriptive title of the knowledge',
		tool: 'Descriptive title of the tool',
		externalApp: 'Select an external app'
	};

	const defaultDescriptions: Record<string, string> = {
		brain: 'In the neural pathways of artificial intelligence, thoughts crystallize into actionable insights, bridging human creativity with computational power.',
		input: 'Through the gateway of information, data flows like streams converging into rivers, carrying the essence of external reality into our digital realm.',
		output: 'At the convergence of processing and presentation, refined insights emerge, transformed and ready to impact the world beyond our computational boundaries.',
		knowledge: 'Within the repository of understanding, wisdom accumulates like sediment in an ancient library, each piece building upon centuries of collective insight.',
		tool: 'Through the mechanism of automation, human intention manifests as precise action, extending our capabilities beyond the limits of manual intervention.',
		externalApp: 'Configure interaction with an external application, specifying read/write permissions and describing the intended operation.'
	};

	// Initialize configuration
	const conf = (node.data.configuration ||= {} as any);
	conf.description ||= defaultDescriptions[node.type] || 'Describe the purpose and function of this node in natural language...';
	
	// For externalApp, initialize app and mode
	if (node.type === 'externalApp') {
		conf.app ||= '';
		// Initialize dynamic fields based on app
		if (conf.app && appFieldConfigs[conf.app]) {
			appFieldConfigs[conf.app].forEach(field => {
				conf[field.key] ||= '';
			});
		}
	}

	// For input nodes, initialize input type and test data
	if (node.type === 'input') {
		conf.inputType ||= 'text';
		conf.testData ||= '';
		inputType = conf.inputType;
		testData = conf.testData;
	}

	// Dynamic content for externalApp
	$: if (node.type === 'externalApp') {
		const appNames = {
			gmail: 'Gmail',
			slack: 'Slack',
			teams: 'Microsoft Teams',
			discord: 'Discord',
			whatsapp: 'WhatsApp Business',
			jira: 'JIRA',
			linear: 'Linear',
			asana: 'Asana',
			monday: 'Monday.com',
			trello: 'Trello',
			salesforce: 'Salesforce',
			hubspot: 'HubSpot',
			pipedrive: 'Pipedrive',
			analytics: 'Google Analytics',
			mixpanel: 'Mixpanel',
			sheets: 'Google Sheets',
			airtable: 'Airtable',
			mailchimp: 'Mailchimp',
			intercom: 'Intercom',
			zapier: 'Zapier',
			github: 'GitHub',
			gitlab: 'GitLab',
			notion: 'Notion',
			confluence: 'Confluence'
		};
		
		const appDescriptions = {
			gmail: 'Connects to Gmail API for reading emails, sending responses, and managing inbox workflows with automation capabilities.',
			slack: 'Connects to Slack API for reading messages, posting responses, and managing channels with automation capabilities.',
			teams: 'Integrates with Microsoft Teams for meeting management, file sharing, and team collaboration automation.',
			discord: 'Links with Discord API for monitoring channels, posting messages, and managing server interactions.',
			whatsapp: 'Connects to WhatsApp Business API for customer support automation and broadcast messaging.',
			jira: 'Integrates with JIRA for automated ticket creation, status updates, and sprint reporting.',
			linear: 'Connects to Linear for issue triage, automated labeling, and progress reporting.',
			asana: 'Links with Asana for project updates, milestone tracking, and team coordination.',
			monday: 'Integrates with Monday.com for status updates, resource allocation, and timeline management.',
			trello: 'Connects to Trello for card automation, progress tracking, and team notifications.',
			salesforce: 'Integrates with Salesforce for lead scoring, opportunity updates, and pipeline management.',
			hubspot: 'Connects to HubSpot for lead nurturing, deal progression, and marketing automation.',
			pipedrive: 'Links with Pipedrive for deal updates, activity logging, and sales reporting.',
			analytics: 'Connects to Google Analytics for traffic analysis, conversion tracking, and audience insights.',
			mixpanel: 'Integrates with Mixpanel for event tracking, user behavior analysis, and cohort studies.',
			sheets: 'Links with Google Sheets for data logging, report generation, and automated calculations.',
			airtable: 'Connects to Airtable for database updates, record creation, and automated workflows.',
			mailchimp: 'Integrates with Mailchimp for email campaigns, subscriber management, and automation sequences.',
			intercom: 'Connects to Intercom for customer messaging, support automation, and user onboarding.',
			zapier: 'Links with Zapier for workflow automation and cross-platform data synchronization.',
			github: 'Integrates with GitHub for issue creation, code review automation, and deployment tracking.',
			gitlab: 'Connects to GitLab for CI/CD automation, issue management, and code quality assurance.',
			notion: 'Interfaces with Notion for knowledge management, document automation, and team wikis.',
			confluence: 'Integrates with Confluence for documentation updates, knowledge sharing, and team collaboration.'
		};
		
		conf.dynamicTitle = conf.app ? `${appNames[conf.app]} Integration` : 'External App Integration';
		conf.tooltipDescription = conf.app ? appDescriptions[conf.app] : 'Configure connection to external applications for automated workflows.';
		conf.currentFields = conf.app ? appFieldConfigs[conf.app] || [] : [];
	}

	function autoresize(el: HTMLTextAreaElement) {
		if (!el) return;
		el.style.height = 'auto';
		el.style.height = `${Math.max(el.scrollHeight, 48)}px`;
	}

	function handleResize(event: Event) {
		const el = event.currentTarget as HTMLTextAreaElement;
		if (el) autoresize(el);
	}

	async function initResize() {
		await tick();
		if (titleEl) autoresize(titleEl);
		if (descEl) autoresize(descEl);
	}

	onMount(() => {
		initResize();
	});

	function handleClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('select');
	}

	function handleMouseDown(e: MouseEvent) {
		// Only start drag if not clicking on input elements or connection ports
		const target = e.target as Element;
		if (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.closest('.connection-port')) {
			return;
		}
		
		e.stopPropagation();
		dispatch('nodestartdrag', { nodeId: node.id, event: e });
	}

	function handleOutputPortMouseDown(e: MouseEvent) {
		e.stopPropagation();
		e.preventDefault();
		
		isDraggingConnection = true;
		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
		connectionStartPoint = {
			x: rect.left + rect.width / 2,
			y: rect.top + rect.height / 2
		};
		connectionCurrentPoint = { ...connectionStartPoint };
		
		dispatch('connectionStart', { nodeId: node.id, port: 'output', startPoint: connectionStartPoint });
		
		// Add global mouse listeners
		document.addEventListener('mousemove', handleConnectionDrag);
		document.addEventListener('mouseup', handleConnectionEnd);
	}

	function handleInputPortMouseDown(e: MouseEvent) {
		e.stopPropagation();
		e.preventDefault();
		
		// Input ports are targets, not sources, so we dispatch a different event
		dispatch('connectionTarget', { nodeId: node.id, port: 'input' });
	}
	
	function handleConnectionDrag(e: MouseEvent) {
		if (!isDraggingConnection || !connectionStartPoint) return;
		
		connectionCurrentPoint = {
			x: e.clientX,
			y: e.clientY
		};
		
		dispatch('connectionDrag', { 
			nodeId: node.id, 
			startPoint: connectionStartPoint, 
			currentPoint: connectionCurrentPoint 
		});
	}
	
	function handleConnectionEnd(e: MouseEvent) {
		if (!isDraggingConnection) return;
		
		isDraggingConnection = false;
		connectionStartPoint = null;
		connectionCurrentPoint = null;
		
		// Check if we're over a valid connection target
		const elementUnderMouse = document.elementFromPoint(e.clientX, e.clientY);
		const targetPort = elementUnderMouse?.closest('.input-port');
		const targetNode = targetPort?.closest('.pocket-note');
		const sourceNode = document.querySelector(`[data-node-id="${node.id}"]`);
		
		if (targetNode && targetNode !== sourceNode && targetPort) {
			const targetNodeId = targetNode.getAttribute('data-node-id');
			if (targetNodeId) {
				dispatch('connectionComplete', { 
					fromNodeId: node.id, 
					toNodeId: targetNodeId,
					fromPort: 'output',
					toPort: 'input'
				});
			}
		} else {
			// Connection cancelled - dropped in empty space
			dispatch('connectionCancel', { nodeId: node.id });
		}
		
		// Remove global listeners
		document.removeEventListener('mousemove', handleConnectionDrag);
		document.removeEventListener('mouseup', handleConnectionEnd);
	}

	function handleDeleteClick(e: MouseEvent) {
		e.stopPropagation();
		dispatch('delete', { nodeId: node.id });
	}

	function handleTitleFocus() {
		focused = true;
		if (!node.data.label || node.data.label.trim() === '') {
			node.data.label = '';
		}
	}

	function handleDescriptionFocus() {
		focused = true;
		if (conf.description === defaultDescriptions[node.type]) {
			conf.description = '';
		}
	}

	function handleKeyActivate(e: KeyboardEvent, action: () => void) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			action();
		}
	}

	// Autocomplete functions for externalApp
	function handleAppInput(e: Event) {
		const target = e.target as HTMLInputElement;
		appSearchQuery = target.value;
		conf.app = '';
		showAppAutocomplete = appSearchQuery.length > 0;
		selectedAppIndex = -1;
	}

	function selectApp(appId: string) {
		conf.app = appId;
		const selectedApp = availableApps.find(a => a.id === appId);
		appSearchQuery = selectedApp?.name || '';
		showAppAutocomplete = false;
		selectedAppIndex = -1;
		
		// Initialize fields for the selected app
		if (selectedApp && appFieldConfigs[appId]) {
			appFieldConfigs[appId].forEach(field => {
				conf[field.key] ||= '';
			});
		}
	}

	function handleAppKeyDown(e: KeyboardEvent) {
		if (!showAppAutocomplete) return;
		
		switch (e.key) {
			case 'ArrowDown':
				e.preventDefault();
				selectedAppIndex = Math.min(selectedAppIndex + 1, filteredApps.length - 1);
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedAppIndex = Math.max(selectedAppIndex - 1, -1);
				break;
			case 'Enter':
				e.preventDefault();
				if (selectedAppIndex >= 0 && filteredApps[selectedAppIndex]) {
					selectApp(filteredApps[selectedAppIndex].id);
				}
				break;
			case 'Escape':
				showAppAutocomplete = false;
				selectedAppIndex = -1;
				break;
		}
	}

	function handleAppFocus() {
		// Show all apps if input is empty, or filtered apps if there's a query
		showAppAutocomplete = true;
		if (appSearchQuery.length === 0) {
			selectedAppIndex = -1;
		}
	}

	function handleAppBlur() {
		// Delay hiding to allow for clicks on dropdown items
		setTimeout(() => {
			showAppAutocomplete = false;
			selectedAppIndex = -1;
		}, 150);
	}

	// Input Node interaction handlers
	function handleInputChange() {
		testData = inputValue;
		conf.testData = testData;
		conf.inputType = inputType;
	}

	function handleFileChange() {
		if (files && files.length > 0) {
			const fileNames = Array.from(files).map(f => f.name).join(', ');
			testData = `Files: ${fileNames}`;
			conf.testData = testData;
		}
	}

	function handleButtonClick() {
		testData = `Button "${inputValue || 'Click Me'}" clicked`;
		conf.testData = testData;
	}

	function handleFormChange() {
		const formData = formFields.map(f => `${f.label}: ${f.value}`).filter(f => f.split(': ')[1]).join(', ');
		testData = formData || 'Form data: (empty)';
		conf.testData = testData;
	}

	function handleChoiceChange() {
		testData = `Selected: ${selectedChoice}`;
		conf.testData = testData;
	}

	function handleTypeChange(type: string) {
		inputType = type;
		conf.inputType = type;
		showTypeSelector = false;
		
		// Reset values when changing type
		inputValue = '';
		files = null;
		selectedChoice = '';
		formFields.forEach(f => f.value = '');
		testData = '';
		conf.testData = '';
	}
</script>

<div 
	class="pocket-note {node.type}"
	class:selected
	class:focused
	class:hovering
	class:dropdown-open={showAppAutocomplete}
	class:dragging-connection={isDraggingConnection}
	style="left: {node.position.x}px; top: {node.position.y}px; --accent-color: {nodeColors[node.type]};"
	data-node-id={node.id}
	on:click={handleClick}
	on:mousedown={handleMouseDown}
	on:mouseenter={() => hovering = true}
	on:mouseleave={() => hovering = false}
	role="button"
	aria-pressed={selected}
	aria-label="{nodeTypeLabels[node.type]} {node.data.label}"
	tabindex="0"
	in:scale={{ duration: 600, easing: elasticOut, start: 0.8 }}
>
	<!-- Input Port Area - left edge hover zone -->
	<div 
		class="port-hover-zone input-zone"
		on:mouseenter={() => showInputPort = true}
		on:mouseleave={() => showInputPort = false}
		role="button"
		aria-label="Input connection area"
		tabindex="-1"
	>
		<div 
			class="connection-port input-port"
			on:mousedown={handleInputPortMouseDown}
			title="Connect to this node"
			role="button"
			aria-label="Connect to this node"
			tabindex="0"
		></div>
	</div>

	<!-- Floating animation icon -->
	{#if hovering}
		<div class="animation-icon" in:fly={{ y: -20, duration: 400, easing: cubicInOut }}>
			<svelte:component this={nodeAnimationIcons[node.type]} size={16} />
		</div>
	{/if}
	
	<button 
		class="delete-button" 
		on:click={handleDeleteClick}
		title="Delete node"
	>
		×
	</button>
	
	<div class="node-type">
		<svelte:component this={nodeIcons[node.type]} size={14} /> 
		{nodeTypeLabels[node.type]}
		{#if node.type === 'externalApp'}
			<div class="info-icon" title={conf.tooltipDescription || 'Configure external app integration'}>
				ⓘ
			</div>
		{/if}
	</div>
	
	{#if node.type === 'externalApp'}
		<!-- Main Title -->
		<div class="main-title">
			{conf.dynamicTitle}
		</div>
		
		<!-- Configuration Fields -->
		<div class="config-fields">
			<!-- App Selection with Autocomplete -->
			<div class="input-group">
				<label class="input-label" for="app-input-{node.id}">App</label>
				<div class="input-container">
					<input
						id="app-input-{node.id}"
						type="text"
						class="config-input"
						placeholder="Start typing app name..."
						bind:value={appSearchQuery}
						on:input={handleAppInput}
						on:keydown={handleAppKeyDown}
						on:focus={handleAppFocus}
						on:blur={handleAppBlur}
					/>
					{#if showAppAutocomplete && filteredApps.length > 0}
						<div class="autocomplete-dropdown" on:click|stopPropagation>
							{#each filteredApps as app, index}
								<button 
									type="button"
									class="autocomplete-item"
									class:selected={selectedAppIndex === index}
									on:click|stopPropagation={() => selectApp(app.id)}
									on:mouseenter={() => selectedAppIndex = index}
								>
									<span class="app-icon">{app.icon}</span>
									<div class="app-info">
										<div class="app-name">{app.name}</div>
										<div class="app-description">{app.description}</div>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			</div>
			
			<!-- Dynamic Fields based on selected app -->
			{#if conf.app && conf.currentFields && conf.currentFields.length > 0}
				{#each conf.currentFields as field}
					<div class="input-group">
						<label class="input-label" for="{field.key}-input-{node.id}">{field.label}</label>
						<input
							id="{field.key}-input-{node.id}"
							type="text"
							class="config-input"
							placeholder={field.placeholder}
							bind:value={conf[field.key]}
						/>
					</div>
				{/each}
			{/if}
		</div>
	{:else if node.type === 'input'}
		<!-- Interactive Input Node -->
		<div class="input-node-container">
			<!-- Input Area -->
			<div class="input-area">
				{#if inputType === 'text'}
					<textarea
						class="interactive-input text-input"
						placeholder="Type your input here..."
						bind:value={inputValue}
						on:input={handleInputChange}
						on:mousedown|stopPropagation
						rows="4"
					></textarea>
				{:else if inputType === 'file'}
					<div class="file-upload-zone" class:has-files={files && files.length > 0}>
						<input
							type="file"
							multiple
							bind:files
							on:change={handleFileChange}
							id="file-input-{node.id}"
							class="file-input"
						/>
						<label for="file-input-{node.id}" class="file-upload-label">
							{#if files && files.length > 0}
								<div class="file-count">{files.length} file{files.length > 1 ? 's' : ''} selected</div>
								<div class="file-names">
									{#each Array.from(files) as file}
										<div class="file-name">{file.name}</div>
									{/each}
								</div>
							{:else}
								<div class="upload-icon">📁</div>
								<div class="upload-text">Drop files here or click to upload</div>
							{/if}
						</label>
					</div>
				{:else if inputType === 'button'}
					<div class="button-container">
						<button class="interactive-button" on:click={handleButtonClick} on:mousedown|stopPropagation>
							{inputValue || 'Click Me'}
						</button>
						<input
							type="text"
							class="button-label-input"
							placeholder="Button label..."
							bind:value={inputValue}
							on:mousedown|stopPropagation
						/>
					</div>
				{:else if inputType === 'form'}
					<div class="form-container">
						{#each formFields as field, i}
							<div class="form-field">
								<label class="form-label" for="form-{i}-{node.id}">{field.label}</label>
								{#if field.type === 'email'}
									<input
										id="form-{i}-{node.id}"
										type="email"
										class="form-input"
										bind:value={field.value}
										on:input={() => handleFormChange()}
										on:mousedown|stopPropagation
									/>
								{:else}
									<input
										id="form-{i}-{node.id}"
										type="text"
										class="form-input"
										bind:value={field.value}
										on:input={() => handleFormChange()}
										on:mousedown|stopPropagation
									/>
								{/if}
							</div>
						{/each}
					</div>
				{:else if inputType === 'multiple-choice'}
					<div class="multiple-choice-container">
						{#each multipleChoiceOptions as option, i}
							<label class="choice-option">
								<input
									type="radio"
									bind:group={selectedChoice}
									value={option}
									on:change={handleChoiceChange}
								/>
								{option}
							</label>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Type Selector -->
			<div class="type-selector-container">
				<button 
					class="type-selector"
					on:click={() => showTypeSelector = !showTypeSelector}
					on:mousedown|stopPropagation
				>
					{inputType === 'multiple-choice' ? 'Multiple Choice' : inputType.charAt(0).toUpperCase() + inputType.slice(1)} ▼
				</button>
				
				{#if showTypeSelector}
					<div class="type-dropdown">
						{#each ['text', 'file', 'button', 'form', 'multiple-choice'] as type}
							<button 
								class="type-option"
								class:selected={inputType === type}
								on:click={() => handleTypeChange(type)}
								on:mousedown|stopPropagation
							>
								{type === 'multiple-choice' ? 'Multiple Choice' : type.charAt(0).toUpperCase() + type.slice(1)}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Test Data Display -->
			{#if testData}
				<div class="test-data">
					<div class="test-data-label">Test Data:</div>
					<div class="test-data-value">{testData}</div>
				</div>
			{/if}
		</div>
	{:else}
		<textarea
			bind:this={titleEl}
			class="title"
			placeholder={defaultTitles[node.type]}
			bind:value={node.data.label}
			on:mousedown|stopPropagation
			on:focus={handleTitleFocus}
			on:blur={() => focused = false}
			on:input={handleResize}
			rows="1"
		/>
	{/if}
	
	{#if node.type !== 'input'}
		<textarea
			bind:this={descEl}
			class="description"
			class:external-app-description={node.type === 'externalApp'}
			placeholder={node.type === 'externalApp' ? 'Describe how this integration should behave in natural language... (e.g., "Send a welcome email when a new user signs up", "Create a JIRA ticket when an error occurs", "Post to Slack when deployment completes")' : 'Describe what this node does in natural language...'}
			bind:value={conf.description}
			on:mousedown|stopPropagation
			on:focus={handleDescriptionFocus}
			on:blur={() => focused = false}
			on:input={handleResize}
			rows={node.type === 'externalApp' ? 4 : 3}
		/>
	{/if}

	<!-- Output Port Area - right edge hover zone -->
	<div 
		class="port-hover-zone output-zone"
		on:mouseenter={() => showOutputPort = true}
		on:mouseleave={() => showOutputPort = false}
		role="button"
		aria-label="Output connection area"
		tabindex="-1"
	>
		<div 
			class="connection-port output-port"
			on:mousedown={handleOutputPortMouseDown}
			title="Create connection from this node"
			role="button"
			aria-label="Create connection from this node"
			tabindex="0"
		></div>
	</div>

	<!-- App Autocomplete Suggestions -->
	{#if showAppAutocomplete && filteredApps.length > 0}
		<div class="autocomplete-suggestions">
			{#each filteredApps as app, index (app.id)}
				<div 
					class="suggestion-item {index === selectedAppIndex ? 'selected' : ''}"
					on:click={() => selectApp(app.id)}
					role="button"
					aria-label={`Select ${app.name}`}
					tabindex="0"
					on:keydown={handleAppKeyDown}
				>
					<span class="app-icon">{app.icon}</span>
					<span class="app-name">{app.name}</span>
					<span class="app-description">{app.description}</span>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.pocket-note {
		position: absolute;
		width: 320px;
		min-height: 240px;
		background: linear-gradient(135deg, #FFFFFF 0%, #FEFEFE 100%);
		border: 1px solid rgba(0, 0, 0, 0.06);
		border-radius: 24px;
		padding: 32px;
		box-shadow: 
			0 4px 32px rgba(0, 0, 0, 0.04),
			0 1px 2px rgba(0, 0, 0, 0.02);
		cursor: pointer;
		transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
		/* Ensure connector ports that extend beyond the card edges remain visible */
		overflow: visible;
	}

	/* Allow dropdown to overflow when autocomplete is open */
	.pocket-note.dropdown-open {
		overflow: visible;
	}

	.pocket-note:hover {
		transform: translateY(-8px) scale(1.02);
		box-shadow: 
			0 16px 64px rgba(0, 0, 0, 0.08),
			0 4px 16px rgba(0, 0, 0, 0.04);
		border-color: color-mix(in oklch, var(--accent-color) 15%, transparent);
	}

	.pocket-note.focused {
		transform: translateY(-4px) scale(1.01);
		box-shadow: 
			0 12px 48px color-mix(in oklch, var(--accent-color) 8%, transparent),
			0 0 0 3px color-mix(in oklch, var(--accent-color) 10%, transparent);
		border-color: color-mix(in oklch, var(--accent-color) 20%, transparent);
	}

	.pocket-note.selected {
		box-shadow: 
			0 0 0 3px color-mix(in oklch, var(--accent-color) 15%, transparent),
			0 12px 48px rgba(0, 0, 0, 0.08);
		border-color: color-mix(in oklch, var(--accent-color) 25%, transparent);
		transform: translateY(-4px) scale(1.01);
	}

	.animation-icon {
		position: absolute;
		top: 16px;
		right: 16px;
		color: var(--accent-color);
		opacity: 0.6;
		animation: float 3s ease-in-out infinite;
	}

	@keyframes float {
		0%, 100% { transform: translateY(0) rotate(0deg); }
		33% { transform: translateY(-4px) rotate(2deg); }
		66% { transform: translateY(-2px) rotate(-1deg); }
	}

	.node-type {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		font-weight: 500;
		color: var(--accent-color);
		margin-bottom: 20px;
		letter-spacing: 0.2px;
		opacity: 0.8;
	}

	.title {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 36px;
		font-weight: 300;
		color: #E5E5E5;
		line-height: 1.2;
		margin-bottom: 20px;
		resize: none;
		overflow: hidden;
		font-family: inherit;
		transition: all 0.3s ease;
	}

	.title:focus,
	.title:not(:placeholder-shown) {
		color: #1F2937;
	}

	.title::placeholder {
		color: #E5E5E5;
	}

	.description {
		width: 100%;
		background: transparent;
		border: none;
		outline: none;
		font-size: 16px;
		font-weight: 400;
		color: #6B7280;
		line-height: 1.6;
		resize: none;
		overflow: hidden;
		font-family: inherit;
		min-height: 80px;
		transition: all 0.3s ease;
	}

	.description:focus {
		color: #374151;
	}

	.description::placeholder {
		color: #D1D5DB;
	}

	.port-hover-zone {
		position: absolute;
		width: 30px;
		height: 60px;
		top: 50%;
		transform: translateY(-50%);
		z-index: 998;
		/* Invisible hover zone (no debug background) */
		background: transparent;
	}

	.input-zone {
		left: -15px;
	}

	.output-zone {
		right: -15px;
	}

	.connection-port {
		position: absolute;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		cursor: pointer;
		top: 50%;
		transform: translateY(-50%);
		z-index: 9999;
		box-shadow: 
			0 4px 12px rgba(0, 0, 0, 0.3),
			0 0 0 2px rgba(255, 255, 255, 1);
		transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
		opacity: 0.6; /* Subtle visibility by default */
		pointer-events: all;
	}

	/* Show ports clearly when hovering a node or dragging a connection from it */
	.pocket-note.hovering .connection-port,
	.pocket-note.dragging-connection .connection-port,
	.pocket-note.selected .connection-port {
		opacity: 1;
		transform: translateY(-50%) scale(1.1);
	}

	.input-port {
		left: -10px;
		background: linear-gradient(135deg, #10B981, #059669);
		position: relative;
	}

	.input-port::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		width: 8px;
		height: 8px;
		background: rgba(255, 255, 255, 0.9);
		border-radius: 50%;
		transform: translate(-50%, -50%);
		transition: all 0.2s ease;
	}

	.output-port {
		right: -10px;
		background: linear-gradient(135deg, #3B82F6, #2563EB);
		position: relative;
	}

	.output-port::after {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		width: 0;
		height: 0;
		border-left: 4px solid rgba(255, 255, 255, 0.9);
		border-top: 3px solid transparent;
		border-bottom: 3px solid transparent;
		transform: translate(-30%, -50%);
		transition: all 0.2s ease;
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.3);
		box-shadow: 
			0 6px 20px rgba(0, 0, 0, 0.4),
			0 0 0 3px rgba(255, 255, 255, 1),
			0 0 16px color-mix(in oklch, var(--accent-color) 40%, transparent);
	}

	.input-port:hover::after {
		width: 10px;
		height: 10px;
		background: rgba(255, 255, 255, 1);
	}

	.output-port:hover::after {
		border-left-width: 5px;
		border-top-width: 4px;
		border-bottom-width: 4px;
		border-left-color: rgba(255, 255, 255, 1);
	}

	/* Node type specific hover animations */
	.pocket-note.hovering .title {
		transform: translateY(-2px);
	}

	.pocket-note.hovering .description {
		transform: translateY(-1px);
	}

	/* Brain node pulse effect */
	.pocket-note.brain.hovering {
		animation: brainPulse 2s ease-in-out infinite;
	}

	@keyframes brainPulse {
		0%, 100% { box-shadow: 0 16px 64px rgba(0, 0, 0, 0.08), 0 4px 16px rgba(0, 0, 0, 0.04); }
		50% { box-shadow: 0 16px 64px rgba(139, 92, 246, 0.1), 0 4px 16px rgba(139, 92, 246, 0.06); }
	}

	/* Delete button area */
	.delete-button {
		position: absolute;
		top: 8px;
		right: 8px;
		width: 20px;
		height: 20px;
		border: none;
		background: transparent;
		color: rgba(0, 0, 0, 0.1);
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		z-index: 10;
		line-height: 1;
		padding: 0;
		opacity: 0;
		transform: scale(0.8);
	}

	.pocket-note:hover .delete-button {
		opacity: 1;
		transform: scale(1);
		color: rgba(0, 0, 0, 0.3);
	}

	.delete-button:hover {
		color: #ef4444 !important;
	}

	/* External App Node Styles - Clean Interface */
	.info-icon {
		margin-left: 8px;
		color: #9CA3AF;
		font-size: 12px;
		cursor: help;
		transition: color 0.2s ease;
	}

	.info-icon:hover {
		color: var(--accent-color);
	}

	.main-title {
		font-size: 18px;
		font-weight: 600;
		color: #111827;
		line-height: 1.4;
		margin-bottom: 20px;
		padding: 0;
		border: none;
		background: transparent;
		resize: none;
		outline: none;
		font-family: inherit;
	}

	.config-fields {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.input-group {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.input-label {
		font-size: 11px;
		font-weight: 500;
		color: #6B7280;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin: 0;
	}

	.input-container {
		position: relative;
		width: 100%;
	}

	.config-input {
		width: 100%;
		padding: 10px 12px;
		border: 1px solid rgba(0, 0, 0, 0.08);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.8);
		font-size: 13px;
		color: #111827;
		font-family: inherit;
		transition: all 0.2s ease;
		box-sizing: border-box;
	}

	.config-input:focus {
		outline: none;
		border-color: var(--accent-color);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent-color) 15%, transparent);
		background: #FFFFFF;
	}

	.config-input::placeholder {
		color: #9CA3AF;
	}

	.config-textarea {
		width: 100%;
		padding: 10px 12px;
		border: 1px solid rgba(0, 0, 0, 0.08);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.8);
		font-size: 13px;
		color: #111827;
		font-family: inherit;
		transition: all 0.2s ease;
		box-sizing: border-box;
		resize: vertical;
		min-height: 80px;
	}

	.config-textarea:focus {
		outline: none;
		border-color: var(--accent-color);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent-color) 15%, transparent);
		background: #FFFFFF;
	}

	.config-textarea::placeholder {
		color: #9CA3AF;
		font-style: italic;
	}

	.autocomplete-dropdown {
		position: absolute;
		top: 100%;
		left: 0;
		right: 0;
		background: #FFFFFF;
		border: 2px solid #EC4899;
		border-radius: 8px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
		z-index: 9999;
		max-height: 300px;
		overflow-y: auto;
		margin-top: 4px;
		min-width: 250px;
	}

	.autocomplete-item {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 12px;
		cursor: pointer;
		transition: background-color 0.2s ease;
		border-radius: 6px;
		margin: 2px;
		border: none;
		background: transparent;
		width: 100%;
		text-align: left;
		font-family: inherit;
	}

	.autocomplete-item:hover,
	.autocomplete-item.selected {
		background: rgba(236, 72, 153, 0.1);
	}

	.app-icon {
		font-size: 16px;
		min-width: 20px;
	}

	.app-info {
		flex: 1;
		min-width: 0;
	}

	.app-name {
		font-size: 13px;
		font-weight: 500;
		color: #111827;
		margin-bottom: 2px;
	}

	.app-description {
		font-size: 11px;
		color: #6B7280;
	}

	/* Dropdown open styles */
	.pocket-note.dropdown-open {
		border-color: color-mix(in oklch, var(--accent-color) 25%, transparent);
		box-shadow: 
			0 12px 48px color-mix(in oklch, var(--accent-color) 10%, transparent),
			0 4px 16px rgba(0, 0, 0, 0.04);
	}

	/* Subtle Delete Button */
	.delete-button {
		position: absolute;
		top: 8px;
		right: 8px;
		width: 20px;
		height: 20px;
		border: none;
		background: transparent;
		color: rgba(0, 0, 0, 0.1);
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		z-index: 10;
		line-height: 1;
		padding: 0;
		opacity: 0;
		transform: scale(0.8);
	}

	.pocket-note:hover .delete-button {
		opacity: 1;
		transform: scale(1);
		color: rgba(0, 0, 0, 0.3);
	}

	.delete-button:hover {
		color: #ef4444 !important;
		background: rgba(239, 68, 68, 0.1);
		transform: scale(1.1) !important;
	}

	/* Additional spacing for external app description */
	.description.external-app-description {
		margin-top: 20px;
	}

	/* Interactive Input Node Styles */
	.input-node-container {
		display: flex;
		flex-direction: column;
		gap: 6px;
		width: 100%;
		height: 176px; /* Fixed height to match other nodes' content area */
	}

	.input-area {
		flex: 1;
		position: relative;
		display: flex;
		flex-direction: column;
	}

	.interactive-input {
		width: 100%;
		flex: 1;
		min-height: 100px;
		padding: 12px;
		border: 2px solid rgba(0, 0, 0, 0.08);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.9);
		font-size: 14px;
		color: #111827;
		font-family: inherit;
		transition: all 0.2s ease;
		box-sizing: border-box;
		resize: none;
		outline: none;
	}

	.interactive-input:focus {
		border-color: var(--accent-color);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--accent-color) 15%, transparent);
		background: #FFFFFF;
	}

	.file-upload-zone {
		position: relative;
		width: 100%;
		flex: 1;
		min-height: 100px;
		border: 2px dashed rgba(0, 0, 0, 0.2);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.5);
		transition: all 0.2s ease;
	}

	.file-upload-zone:hover {
		border-color: var(--accent-color);
		background: rgba(255, 255, 255, 0.8);
	}

	.file-upload-zone.has-files {
		border-style: solid;
		border-color: var(--accent-color);
		background: color-mix(in oklch, var(--accent-color) 5%, white);
	}

	.file-input {
		position: absolute;
		width: 100%;
		height: 100%;
		opacity: 0;
		cursor: pointer;
	}

	.file-upload-label {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		cursor: pointer;
		color: #6B7280;
		text-align: center;
		gap: 6px;
		padding: 8px;
	}

	.upload-icon {
		font-size: 20px;
	}

	.upload-text {
		font-size: 12px;
		font-weight: 500;
	}

	.file-count {
		font-size: 14px;
		font-weight: 600;
		color: var(--accent-color);
	}

	.file-names {
		display: flex;
		flex-direction: column;
		gap: 2px;
		max-height: 60px;
		overflow-y: auto;
	}

	.file-name {
		font-size: 11px;
		color: #6B7280;
		max-width: 200px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.button-container {
		display: flex;
		flex-direction: column;
		gap: 6px;
		flex: 1;
		min-height: 100px;
		justify-content: center;
	}

	.interactive-button {
		width: 100%;
		padding: 12px 24px;
		background: var(--accent-color);
		color: white;
		border: none;
		border-radius: 8px;
		font-size: 14px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.interactive-button:hover {
		background: color-mix(in oklch, var(--accent-color) 85%, black);
		transform: translateY(-1px);
		box-shadow: 0 4px 12px color-mix(in oklch, var(--accent-color) 25%, transparent);
	}

	.button-label-input {
		width: 100%;
		padding: 6px 8px;
		border: 1px solid rgba(0, 0, 0, 0.08);
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.8);
		font-size: 11px;
		color: #6B7280;
		outline: none;
	}

	.button-label-input:focus {
		border-color: var(--accent-color);
		box-shadow: 0 0 0 2px color-mix(in oklch, var(--accent-color) 15%, transparent);
	}

	.form-container {
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex: 1;
		min-height: 100px;
	}

	.form-field {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.form-label {
		font-size: 10px;
		font-weight: 500;
		color: #6B7280;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.form-input {
		padding: 6px 8px;
		border: 1px solid rgba(0, 0, 0, 0.08);
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.9);
		font-size: 12px;
		color: #111827;
		outline: none;
		transition: all 0.2s ease;
	}

	.form-input:focus {
		border-color: var(--accent-color);
		box-shadow: 0 0 0 2px color-mix(in oklch, var(--accent-color) 15%, transparent);
		background: #FFFFFF;
	}

	.multiple-choice-container {
		display: flex;
		flex-direction: column;
		gap: 6px;
		flex: 1;
		min-height: 100px;
	}

	.choice-option {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 8px;
		border-radius: 6px;
		cursor: pointer;
		transition: background 0.2s ease;
		font-size: 12px;
		color: #111827;
	}

	.choice-option:hover {
		background: rgba(0, 0, 0, 0.03);
	}

	.choice-option input[type="radio"] {
		margin: 0;
		accent-color: var(--accent-color);
	}

	.type-selector-container {
		position: relative;
		align-self: flex-start;
		margin-top: 4px;
	}

	.type-selector {
		padding: 3px 6px;
		background: rgba(255, 255, 255, 0.8);
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 5px;
		font-size: 10px;
		color: #6B7280;
		cursor: pointer;
		transition: all 0.2s ease;
		text-transform: capitalize;
		font-weight: 500;
	}

	.type-selector:hover {
		border-color: var(--accent-color);
		color: var(--accent-color);
		background: color-mix(in oklch, var(--accent-color) 5%, white);
	}

	.type-dropdown {
		position: absolute;
		bottom: 100%;
		right: 0;
		margin-bottom: 4px;
		background: white;
		border: 1px solid rgba(0, 0, 0, 0.1);
		border-radius: 8px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
		z-index: 20;
		min-width: 120px;
		overflow: hidden;
	}

	.type-option {
		width: 100%;
		padding: 8px 12px;
		background: transparent;
		border: none;
		text-align: left;
		font-size: 12px;
		color: #374151;
		cursor: pointer;
		transition: background 0.2s ease;
		text-transform: capitalize;
	}

	.type-option:hover {
		background: rgba(0, 0, 0, 0.05);
	}

	.type-option.selected {
		background: color-mix(in oklch, var(--accent-color) 10%, white);
		color: var(--accent-color);
		font-weight: 600;
	}

	.test-data {
		padding: 6px 8px;
		border-radius: 6px;
		background: color-mix(in oklch, var(--accent-color) 5%, white);
		border: 1px solid color-mix(in oklch, var(--accent-color) 20%, transparent);
		margin-top: 6px;
		flex-shrink: 0;
	}

	.test-data-label {
		font-size: 9px;
		font-weight: 600;
		color: var(--accent-color);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 2px;
	}

	.test-data-value {
		font-size: 11px;
		color: #374151;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		word-break: break-word;
		line-height: 1.3;
	}
</style>
'''
