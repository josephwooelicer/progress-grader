import * as vscode from "vscode";
import { backendGet, backendPost } from "../api/client";
import { getConfig } from "../config";

const CONSENT_KEY = "progressGrader.consented";

interface ConsentTextResponse {
  text: string;
}

interface ConsentResponse {
  ok: boolean;
  already_consented: boolean;
}

/**
 * Ensure the student has consented for this project.
 * Shows a blocking modal if not. Returns false if the student declines.
 */
export async function ensureConsent(
  context: vscode.ExtensionContext
): Promise<boolean> {
  const config = getConfig();
  const storageKey = `${CONSENT_KEY}.${config.projectId}`;

  // Fast path: already recorded locally
  if (context.workspaceState.get<boolean>(storageKey)) {
    return true;
  }

  // Check server (handles re-installs / new devices)
  try {
    const resp = await backendPost<ConsentResponse>("/api/consent", {
      project_id: config.projectId,
    });
    if (resp.already_consented) {
      await context.workspaceState.update(storageKey, true);
      return true;
    }
  } catch {
    // Network error — fall through to show modal
  }

  // Show consent modal
  let consentText =
    "I consent to the collection and storage of my AI conversation history " +
    "and Git activity for this project for grading purposes.";

  try {
    const resp = await backendGet<ConsentTextResponse>("/api/consent/text");
    consentText = resp.text;
  } catch {
    // use default text
  }

  const choice = await vscode.window.showInformationMessage(
    "Progress Grader — Data Collection Consent",
    {
      modal: true,
      detail:
        `${consentText}\n\n` +
        "You must consent to use the AI assistant in this project. " +
        "This consent is permanent and cannot be revoked.",
    },
    "I Agree",
    "Decline"
  );

  if (choice !== "I Agree") {
    vscode.window.showWarningMessage(
      "Progress Grader: AI assistant is disabled until you consent."
    );
    return false;
  }

  try {
    await backendPost<ConsentResponse>("/api/consent", {
      project_id: config.projectId,
    });
    await context.workspaceState.update(storageKey, true);
  } catch (err) {
    vscode.window.showErrorMessage(
      `Progress Grader: Failed to record consent — ${String(err)}`
    );
    return false;
  }

  return true;
}
