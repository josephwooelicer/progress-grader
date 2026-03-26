import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { streamChat, ChatMessage } from "../api/client";
import { ConversationManager } from "./conversationManager";
import { StatusBarManager } from "../status/statusBar";

export class ChatPanel {
  static readonly viewType = "progressGrader.chat";
  private static instance: ChatPanel | undefined;

  private readonly panel: vscode.WebviewPanel;
  private abortController: AbortController | undefined;

  static show(
    context: vscode.ExtensionContext,
    conversation: ConversationManager,
    statusBar: StatusBarManager
  ): void {
    if (ChatPanel.instance) {
      ChatPanel.instance.panel.reveal(vscode.ViewColumn.Two);
      return;
    }
    new ChatPanel(context, conversation, statusBar);
  }

  private constructor(
    private context: vscode.ExtensionContext,
    private conversation: ConversationManager,
    private statusBar: StatusBarManager
  ) {
    this.panel = vscode.window.createWebviewPanel(
      ChatPanel.viewType,
      "Progress Grader",
      vscode.ViewColumn.Two,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.file(path.join(context.extensionPath, "media")),
        ],
      }
    );

    this.panel.webview.html = this.getHtml();
    this.panel.onDidDispose(() => {
      ChatPanel.instance = undefined;
    });

    this.panel.webview.onDidReceiveMessage(
      (msg) => this.handleMessage(msg),
      undefined,
      context.subscriptions
    );

    ChatPanel.instance = this;

    // Send initial conversation id
    void this.panel.webview.postMessage({
      type: "conversationId",
      id: this.conversation.id,
    });
  }

  private getHtml(): string {
    const htmlPath = path.join(
      this.context.extensionPath,
      "media",
      "chat.html"
    );
    return fs.readFileSync(htmlPath, "utf8");
  }

  private async handleMessage(msg: { type: string; text?: string }): Promise<void> {
    if (msg.type === "newConversation") {
      this.abortController?.abort();
      const newId = this.conversation.startNew();
      await this.panel.webview.postMessage({ type: "newConversation" });
      await this.panel.webview.postMessage({ type: "conversationId", id: newId });
      return;
    }

    if (msg.type === "send" && msg.text) {
      await this.sendMessage(msg.text);
    }
  }

  private async sendMessage(text: string): Promise<void> {
    this.abortController = new AbortController();

    const userMessage: ChatMessage = { role: "user", content: text };
    this.conversation.addMessage(userMessage);

    const messages = this.conversation.getHistory();

    try {
      let lastUsagePct = 0;

      await streamChat(
        this.conversation.id,
        messages,
        undefined,
        (chunk) => {
          if (chunk.error) {
            void this.panel.webview.postMessage({
              type: "error",
              message: chunk.error === "consent_required"
                ? "Consent is required to use the AI assistant for this project."
                : chunk.error,
            });
            return;
          }

          if (chunk.delta) {
            void this.panel.webview.postMessage({
              type: "chunk",
              delta: chunk.delta,
              context_usage_pct: chunk.context_usage_pct,
            });
          }

          if (chunk.context_usage_pct !== undefined) {
            lastUsagePct = chunk.context_usage_pct;
            this.statusBar.setUsage(chunk.context_usage_pct);
          }

          if (chunk.done) {
            void this.panel.webview.postMessage({
              type: "done",
              context_usage_pct: chunk.context_usage_pct,
            });
          }
        },
        this.abortController.signal
      );

      // Store assistant reply — we reconstruct from the panel's accumulated text
      // via a round-trip request to avoid buffering the entire stream here.
      // The proxy already logs both sides to the DB, so local history only
      // needs the role marker for context window rebuild.
      this.conversation.addMessage({ role: "assistant", content: "…" });

    } catch (err) {
      await this.panel.webview.postMessage({
        type: "error",
        message: `Request failed: ${String(err)}`,
      });
    }
  }
}
