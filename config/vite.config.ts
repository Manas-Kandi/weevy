import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
	plugins: [sveltekit()],
	resolve: {
		alias: {
			$lib: path.resolve('./src/lib')
		}
	},
	server: {
		port: 3000,
		proxy: {
			'/api': 'http://localhost:8004',
			'/ws': {
				target: 'ws://localhost:8000',
				ws: true
			}
		}
	}
});
