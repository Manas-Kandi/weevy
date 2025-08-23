export class TestingPanel {
  private panelId: string;

  constructor(panelId: string) {
    this.panelId = panelId;
    console.log(`Testing Panel initialized with ID: ${panelId}`);
  }

  addCustomLog(message: string, type: 'info' | 'warning' | 'error'): void {
    console.log(`[${type.toUpperCase()}] ${message}`);
  }

  addNodeResult(result: any): void {
    console.log('Node result:', result);
  }

  updatePerformanceMetrics(metrics: Record<string, any>): void {
    console.log('Performance metrics:', metrics);
  }

  appendStreamContent(content: string): void {
    console.log('Stream content:', content);
  }
}