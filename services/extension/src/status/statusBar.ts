import * as vscode from "vscode";

export class StatusBarManager {
  private item: vscode.StatusBarItem;
  private usagePct = 0;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = "progressGrader.openChat";
    this.item.tooltip = "Progress Grader — click to open chat";
    this.render();
    this.item.show();
  }

  setUsage(pct: number): void {
    this.usagePct = Math.min(Math.round(pct * 10) / 10, 100);
    this.render();

    if (this.usagePct >= 100) {
      vscode.window
        .showWarningMessage(
          "Progress Grader: You have reached the context limit for this conversation.",
          "New Conversation"
        )
        .then((choice) => {
          if (choice === "New Conversation") {
            void vscode.commands.executeCommand("progressGrader.newConversation");
          }
        });
    }
  }

  private render(): void {
    const icon =
      this.usagePct >= 90
        ? "$(warning)"
        : this.usagePct >= 70
        ? "$(info)"
        : "$(hubot)";

    this.item.text = `${icon} AI ${this.usagePct}%`;

    if (this.usagePct >= 90) {
      this.item.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.warningBackground"
      );
    } else {
      this.item.backgroundColor = undefined;
    }
  }

  dispose(): void {
    this.item.dispose();
  }
}
