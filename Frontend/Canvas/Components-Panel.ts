export class ComponentsPanel {
  private panelId: string;

  constructor(panelId: string) {
    this.panelId = panelId;
    console.log(`Components Panel initialized with ID: ${panelId}`);
  }

  openNodeConfiguration(node: any): void {
    console.log('Opening node configuration for:', node);
  }

  handleNodeDrop(type: any, position: { x: number; y: number }): void {
    console.log(`Node dropped: ${type} at position`, position);
  }
}