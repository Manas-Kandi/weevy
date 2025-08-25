import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 3000,
		proxy: {
			'/api': 'http://localhost:8004',
			'/ws': {
				target: 'ws://localhost:8004',
				ws: true
			}
		}
	}
});
