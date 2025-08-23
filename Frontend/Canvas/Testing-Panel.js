export class TestingPanel {
    constructor(panelId) {
        this.panelId = panelId;
        console.log(`Testing Panel initialized with ID: ${panelId}`);
    }
    addCustomLog(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    addNodeResult(result) {
        console.log('Node result:', result);
    }
    updatePerformanceMetrics(metrics) {
        console.log('Performance metrics:', metrics);
    }
    appendStreamContent(content) {
        console.log('Stream content:', content);
    }
}
