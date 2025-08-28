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
	let showInputPort = false;
	let showOutputPort = false;
	let titleEl: HTMLTextAreaElement;
	let descEl: HTMLTextAreaElement;
	
	// External App specific state
	let showAppAutocomplete = false;
	let appSearchQuery = '';
	let selectedAppIndex = -1;

	const dispatch = createEventDispatcher<{
		select: void;
		connectionStart: { nodeId: string; port: 'output' };
		connectionEnd: { nodeId: string; port: 'input' };
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
		conf.rules ||= '';
		// Initialize dynamic fields based on app
		if (conf.app && appFieldConfigs[conf.app]) {
			appFieldConfigs[conf.app].forEach(field => {
				conf[field.key] ||= '';
			});
		}
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
		dispatch('connectionStart', { nodeId: node.id, port: 'output' });
	}

	function handleInputPortMouseDown(e: MouseEvent) {
		e.stopPropagation();
		dispatch('connectionEnd', { nodeId: node.id, port: 'input' });
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Delete' || e.key === 'Backspace') {
			e.preventDefault();
			dispatch('delete', { nodeId: node.id });
		}
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
</script>

<div 
	class="pocket-note {node.type}"
	class:selected
	class:focused
	class:hovering
	class:dropdown-open={showAppAutocomplete}
	style="left: {node.position.x}px; top: {node.position.y}px; --accent-color: {nodeColors[node.type]};"
	on:click={handleClick}
	on:mousedown={handleMouseDown}
	on:mouseenter={() => hovering = true}
	on:mouseleave={() => hovering = false}
	role="button"
	aria-pressed={selected}
	aria-label={`${nodeTypeLabels[node.type]} ${node.data.label}`}
	tabindex="0"
	on:keydown={handleKeyDown}
	in:scale={{ duration: 600, easing: elasticOut, start: 0.8 }}
>
	<!-- Input Port Area - invisible hover zone -->
	<div 
		class="port-hover-zone input-zone"
		on:mouseenter={() => showInputPort = true}
		on:mouseleave={() => showInputPort = false}
		role="button"
		aria-label="Input connection area"
		tabindex="-1"
	>
		{#if showInputPort || hovering}
			<div 
				class="connection-port input-port"
				on:mousedown={handleInputPortMouseDown}
				title="Connect to this node"
				role="button"
				aria-label="Connect to this node"
				tabindex="0"
				in:scale={{ duration: 200, start: 0.3 }}
			></div>
		{/if}
	</div>

	<!-- Floating animation icon -->
	{#if hovering}
		<div class="animation-icon" in:fly={{ y: -20, duration: 400, easing: cubicInOut }}>
			<svelte:component this={nodeAnimationIcons[node.type]} size={16} />
		</div>
	{/if}
	
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
				<label class="input-label">App</label>
				<div class="input-container">
					<input
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
								<div 
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
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
			
			<!-- Dynamic Fields based on selected app -->
			{#if conf.app && conf.currentFields && conf.currentFields.length > 0}
				{#each conf.currentFields as field}
					<div class="input-group">
						<label class="input-label">{field.label}</label>
						<input
							type="text"
							class="config-input"
							placeholder={field.placeholder}
							bind:value={conf[field.key]}
						/>
					</div>
				{/each}
			{/if}
			
			<!-- Rules Field for Natural Language Instructions -->
			{#if conf.app}
				<div class="input-group">
					<label class="input-label">Rules</label>
					<textarea
						class="config-textarea"
						placeholder="Describe how this integration should behave in natural language... (e.g., 'Send a welcome email when a new user signs up', 'Create a JIRA ticket when an error occurs', 'Post to Slack when deployment completes')"
						bind:value={conf.rules}
						rows="3"
					></textarea>
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
	
	<textarea
		bind:this={descEl}
		class="description"
		placeholder="Describe what this node does in natural language..."
		bind:value={conf.description}
		on:mousedown|stopPropagation
		on:focus={handleDescriptionFocus}
		on:blur={() => focused = false}
		on:input={handleResize}
		rows="3"
	/>

	<!-- Output Port Area - invisible hover zone -->
	<div 
		class="port-hover-zone output-zone"
		on:mouseenter={() => showOutputPort = true}
		on:mouseleave={() => showOutputPort = false}
		role="button"
		aria-label="Output connection area"
		tabindex="-1"
	>
		{#if showOutputPort || hovering}
			<div 
				class="connection-port output-port"
				on:mousedown={handleOutputPortMouseDown}
				title="Create connection from this node"
				role="button"
				aria-label="Create connection from this node"
				tabindex="0"
				in:scale={{ duration: 200, start: 0.3 }}
			></div>
		{/if}
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
		overflow: hidden;
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
		width: 60px;
		height: 80px;
		top: 50%;
		transform: translateY(-50%);
		z-index: 5;
		/* Invisible hover zone */
	}

	.input-zone {
		left: -50px;
	}

	.output-zone {
		right: -50px;
	}

	.connection-port {
		position: absolute;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		cursor: pointer;
		top: 50%;
		transform: translateY(-50%);
		z-index: 15;
		box-shadow: 
			0 4px 12px rgba(0, 0, 0, 0.15),
			0 0 0 2px rgba(255, 255, 255, 1) inset;
		backdrop-filter: blur(8px);
		transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
	}

	.input-port {
		left: 22px;
		background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
	}

	.output-port {
		right: 22px;
		background: var(--accent-color);
	}

	.connection-port:hover {
		transform: translateY(-50%) scale(1.4);
		box-shadow: 
			0 6px 20px rgba(0, 0, 0, 0.25),
			0 0 0 3px rgba(255, 255, 255, 1) inset,
			0 0 16px color-mix(in oklch, var(--accent-color) 30%, transparent);
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
	.pocket-note.selected::after {
		content: '×';
		position: absolute;
		top: -8px;
		right: -8px;
		width: 24px;
		height: 24px;
		background: #EF4444;
		color: white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		font-weight: 600;
		cursor: pointer;
		box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
		transition: all 0.2s ease;
		z-index: 20;
	}

	.pocket-note.selected:hover::after {
		transform: scale(1.1);
		box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
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
</style>
'''