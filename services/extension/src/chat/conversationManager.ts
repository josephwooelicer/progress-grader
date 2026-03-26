import * as vscode from "vscode";
import { randomUUID } from "crypto";
import { ChatMessage } from "../api/client";

const CONVERSATION_ID_KEY = "progressGrader.currentConversationId";
const HISTORY_KEY_PREFIX = "progressGrader.history.";

export class ConversationManager {
  private conversationId: string;
  private history: ChatMessage[] = [];

  constructor(private context: vscode.ExtensionContext) {
    // Restore or create conversation id
    const stored = context.workspaceState.get<string>(CONVERSATION_ID_KEY);
    this.conversationId = stored ?? this.generateNew();
    this.history =
      context.workspaceState.get<ChatMessage[]>(
        `${HISTORY_KEY_PREFIX}${this.conversationId}`
      ) ?? [];
  }

  get id(): string {
    return this.conversationId;
  }

  getHistory(): ChatMessage[] {
    return [...this.history];
  }

  addMessage(message: ChatMessage): void {
    this.history.push(message);
    void this.context.workspaceState.update(
      `${HISTORY_KEY_PREFIX}${this.conversationId}`,
      this.history
    );
  }

  /** Student explicitly starts a new conversation — grading signal. */
  startNew(): string {
    this.conversationId = this.generateNew();
    this.history = [];
    void this.context.workspaceState.update(
      CONVERSATION_ID_KEY,
      this.conversationId
    );
    return this.conversationId;
  }

  private generateNew(): string {
    const id = randomUUID();
    void this.context.workspaceState.update(CONVERSATION_ID_KEY, id);
    return id;
  }
}
