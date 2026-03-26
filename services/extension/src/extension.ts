import * as vscode from "vscode";
import { getConfig } from "./config";
import { ensureConsent } from "./consent/consentFlow";
import { ConversationManager } from "./chat/conversationManager";
import { ChatPanel } from "./chat/chatPanel";
import { StatusBarManager } from "./status/statusBar";
import { HeartbeatService } from "./heartbeat/heartbeatService";

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  // Validate we are inside a managed workspace
  let config;
  try {
    config = getConfig();
  } catch (err) {
    // Not a managed workspace — extension is dormant
    console.log(`Progress Grader inactive: ${String(err)}`);
    return;
  }

  // Services
  const statusBar = new StatusBarManager();
  const heartbeat = new HeartbeatService();
  const conversation = new ConversationManager(context);

  context.subscriptions.push(
    { dispose: () => statusBar.dispose() },
    { dispose: () => heartbeat.dispose() }
  );

  // Start heartbeat immediately
  heartbeat.start();

  // Ensure consent before allowing any AI interaction
  const consented = await ensureConsent(context);
  if (!consented) {
    statusBar.setUsage(0);
    // Register commands but they will prompt consent again
  }

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("progressGrader.openChat", async () => {
      const ok = await ensureConsent(context);
      if (!ok) return;
      ChatPanel.show(context, conversation, statusBar);
    }),

    vscode.commands.registerCommand("progressGrader.newConversation", () => {
      const newId = conversation.startNew();
      statusBar.setUsage(0);
      vscode.window.showInformationMessage(
        `Progress Grader: Started new conversation (${newId.slice(0, 8)}…)`
      );
      // If chat panel is open, it listens to this command via its own handler
      void vscode.commands.executeCommand("progressGrader.openChat");
    })
  );

  // Open chat automatically on first activation if consented
  if (consented) {
    ChatPanel.show(context, conversation, statusBar);
  }
}

export function deactivate(): void {
  // Cleanup handled via context.subscriptions
}
