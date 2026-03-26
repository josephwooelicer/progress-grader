// ── Timeline ──────────────────────────────────────────────────────────────────

export type TimelineEvent =
  | ConversationStartEvent
  | UserMessageEvent
  | AssistantMessageEvent
  | GitCommitEvent
  | GitBranchCreateEvent
  | GitBranchDeleteEvent
  | GitPROpenEvent
  | GitPRMergeEvent
  | GitForcePushEvent;

export interface ConversationStartEvent {
  type: "conversation_start";
  id: string; // conversation_id
  conversation_id: string;
  timestamp: string;
  model: string;
}

export interface UserMessageEvent {
  type: "user_message";
  id: string;
  conversation_id: string;
  content: string;
  input_tokens: number | null;
  timestamp: string;
}

export interface AssistantMessageEvent {
  type: "assistant_message";
  id: string;
  conversation_id: string;
  content: string;
  output_tokens: number | null;
  timestamp: string;
}

export interface GitCommitEvent {
  type: "git_commit";
  id: string;
  commit_sha: string;
  commit_message: string;
  branch_name: string;
  forced: boolean;
  timestamp: string;
}

export interface GitBranchCreateEvent {
  type: "git_branch_create";
  id: string;
  branch_name: string;
  timestamp: string;
}

export interface GitBranchDeleteEvent {
  type: "git_branch_delete";
  id: string;
  branch_name: string;
  timestamp: string;
}

export interface GitPROpenEvent {
  type: "git_pr_open";
  id: string;
  pr_number: number;
  pr_title: string;
  branch_name: string | null;
  timestamp: string;
}

export interface GitPRMergeEvent {
  type: "git_pr_merge";
  id: string;
  pr_number: number;
  pr_title: string;
  timestamp: string;
}

export interface GitForcePushEvent {
  type: "git_force_push";
  id: string;
  commit_sha: string | null;
  branch_name: string;
  timestamp: string;
}

// ── Raw API event (from backend timeline endpoint) ────────────────────────────

export interface RawTimelineItem {
  type: "conversation_message" | "git_event";
  id: string;
  conversation_id?: string;
  role?: "user" | "assistant";
  content?: string;
  model?: string;
  input_tokens?: number | null;
  output_tokens?: number | null;
  event_type?: string;
  commit_sha?: string | null;
  commit_message?: string | null;
  branch_name?: string | null;
  pr_number?: number | null;
  pr_title?: string | null;
  forced?: boolean;
  created_at: string;
}

// ── Comments & Flags ──────────────────────────────────────────────────────────

export interface TimelineComment {
  id: string;
  teacher_id: string;
  entry_type: string;
  entry_id: string;
  content: string;
  created_at: string;
}

// ── Rubric ────────────────────────────────────────────────────────────────────

export interface RubricDimension {
  id: string;
  project_id: string;
  name: string;
  description: string;
  scoring_criteria: string;
  max_score: number;
  is_mandatory: boolean;
  display_order: number;
}

export interface RubricScore {
  id: string;
  dimension_id: string;
  student_id: string;
  suggested_score: number | null;
  suggested_justification: string | null;
  confirmed_score: number | null;
  confirmed_justification: string | null;
}

// ── People & Projects ─────────────────────────────────────────────────────────

export interface Course {
  id: string;
  name: string;
  slug: string;
  gitea_org: string | null;
  created_at: string;
}

export interface Project {
  id: string;
  course_id: string;
  name: string;
  slug: string;
  description: string | null;
  created_at: string;
}

export interface Student {
  id: string;
  name: string;
  email: string;
  consented: boolean;
}

// ── Git summary ───────────────────────────────────────────────────────────────

export interface GitSummaryStats {
  commits: number;
  force_pushes: number;
  branches_created: number;
  prs_opened: number;
  prs_merged: number;
}
